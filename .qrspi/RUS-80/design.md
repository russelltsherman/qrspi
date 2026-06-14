# Design — Configurable transient-error resilience for qrspi-batch agent jobs

**Ticket:** RUS-80
**Research basis:** research.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Revised:** 2026-06-14 — re-scoped after the OQ1 probe (see Probe Result) invalidated the
signature-classifier mechanism.
**Status:** draft

## Probe Result (was OQ1 — now resolved, and decisive)

OQ1 asked: *when `agent()` fails on a transient network/API error, does the harness throw an
Error carrying the signature, or return a bare `null` with the message discarded?* This was
framed in the prior draft as "the single biggest unknown." It has now been **empirically
resolved** by a probe of the `agent()` failure seam (`.claude/workflows/probe-agent-failure.js`,
3 agents, ~4s), and the answer **breaks the prior design's central deliverable**:

| Induced failure | Layer | Result |
|---|---|---|
| valid call (baseline) | — | returned `"OK"` (string) |
| **invalid `model` id (4xx)** | **API / network** | **`threw=false`, returned bare `null`, message discarded** |
| unknown `agentType` | client-side pre-flight | `threw=true` with full message |

**The transient classes this ticket targets** (429, 529, `socket connection was closed
unexpectedly`, `ECONNRESET`, `fetch failed`, stream `terminated`) all live at the **API/network
layer** — the same layer as the invalid-`model` test, which returned a **bare `null` with the
signature discarded**. The harness *had* the message (it logged `[invalid-model] failed: …`) but
did not hand it to the script. The **only** path that throws a catchable message is client-side
config validation (unknown `agentType`), which a transient network fault can never reach.

Consequences (these drove the re-scope below):

- **A signature-based, default-deny transient classifier has no input at the `agent()` seam.**
  With only `null` visible, there is nothing to match against an allowlist. The prior Decision 1
  Options A and C both assumed a catchable `e.message`; the probe shows that seam does not exist
  for the targeted error classes.
- **OQ2/OQ3 are moot at this layer** — with no signature there is nothing to backoff-retry by
  class or to gate on.
- **OQ4 is confirmed out of reach** — `trunk sync failed` / dirty-tree throws travel a *run-level*
  path that never reaches the `agent()` wrapper. They remain pure-classifier-unit-test concerns
  only if a classifier is built (it is not, below) — otherwise they are simply out of scope here.
- The harness **already retries once** before returning `null` (its documented `agent()` contract),
  so some transient resilience already exists *below* this seam, outside this repo's reach.

The prior draft's classifier/allowlist/backoff/default-deny mechanism is therefore **withdrawn**.
The sections below re-scope the ticket to what is actually buildable at the visible seam.

## Current State

- `agent()` is a harness-injected global, not defined in `qrspi-batch.js`; it is a uniform 2-arg
  call `await agent(promptString, { label, phase, agentType?, schema? })` at ~20 call sites, all
  following the identical convention (ref: Q3).
- On failure or skip, `agent()` returns `null` (or falsy) **without throwing for the targeted
  transient classes** (Probe Result above; ref: Q1). Every consumer treats `null` as "stop this
  ticket, leave it untouched, fabricate nothing." There is exactly one observable return contract
  at this seam and the failure message is discarded before the script sees it.
- A single transient failure therefore aborts the ticket immediately: `runPhase` returns `false`
  → `doDesign`/`doPlan` return `failTicket(t)`; critic loops return `{ ok:false }` → `false`;
  slice/coherence critics return a falsy envelope → `skip(...)`. No retry exists in this repo (the
  harness's own single retry sits below the seam) (ref: Q1, ref: Q7).
- **The error signature the prior feature wanted to classify is NOT available at this seam** and
  cannot be made available from within this repo (Probe Result). A grep for every transient
  signature returns zero hits in code — they are harness-runtime strings the `agent()` contract
  discards (ref: Q2, ref: Q8).
- On a propagated failure nothing is mutated for the ticket: phase agents write to a token-free
  staging path `/tmp/phase-stage/<id>/<artifact>.md` (the `stg()` helper), and `persistArtifact`
  (the real success gate, via `qrspi_persist.py`) moves to the canonical worktree path only after
  producer + node-check + critic loop all succeed; finalize (commit / `gt submit` / Linear write)
  runs only after `runPhase` returns true (ref: Q6).
- **Each phase already persists its artifacts to the worktree before the next phase begins**, and
  `qrspi_resolve.py` performs **artifact detection** + a skip-if-exists resume convention — the
  orchestrator and `run_design`/`advance`/`submit` paths already *skip any phase whose artifact
  exists and is non-empty*. This existing, committed checkpoint behavior is the seam the re-scoped
  feature builds on (ref: Q6, resolver artifact-detection).
- The "resolved-not-hard-coded" config pattern to mirror is the `critics` block: a tested Python
  core (`scripts/qrspi_critics_config.py`) self-locates `REPO_ROOT` from `__file__`, reads
  `.qrspi/config.json` once via `qrspi_config.read_config`, applies config-value > default
  precedence in pure resolvers, and emits an always-complete single-line JSON envelope; JS glue
  (`readCriticsConfig` worker + `parseCriticsEnvelope`) shells out, logs `warnings[]`, and
  shallow-merges over a lockstep `DEFAULT_CRITIC_PHASES` mirror, falling back to defaults on any
  parse failure (ref: Q4).
- `qrspi_config.py` reads ONE top-level key only (no dot-path); a nested block like
  `critics`/`resilience` is read by a dedicated all-keys script, not `qrspi_config.py --key`
  (ref: Q4 implicit contracts).
- The pure-test convention: a stdlib-only assert-based `scripts/<name>_test.py` is auto-discovered
  by `run_tests.py` and gated in CI — zero registration needed (ref: Q11).
- Progress is emitted via the injected `log(...)` global (one pre-formatted string, two-space
  indent, `${id}:` prefix); `phase('<Name>')` sets the coarser group. No log levels (ref: Q13).

## Desired End State (re-scoped)

The ticket's underlying value — *"make batch runs resilient instead of all-or-nothing"* — is
delivered by **checkpoint-and-resume on a mid-ticket bare `null`** rather than by classifying a
signature that is not observable. Concretely:

- **Resume avoids re-burning prior phase spend (primary deliverable).** When a ticket aborts
  mid-run because some phase's `agent()` returned `null`, the *already-completed, already-persisted*
  upstream phases are NOT recomputed on the next batch pass. This is already largely true via the
  existing artifact-detection/skip-if-exists resume — the deliverable is to make it **explicit,
  configurable, observable, and tested**, and to confirm it covers the mid-critic-loop and
  mid-slice abort paths, not only clean phase boundaries.
- **Config in `.qrspi/config.json` under a `resilience` block,** read via the same
  resolved-not-hard-coded mechanism as `critics`, with sensible defaults when absent (ref: Q4).
  The block carries `resumeOnNull` (default ON — the resilience baseline the ticket frames) and,
  if the optional re-attempt below is adopted, `singleReattempt`/`reattemptCap`.
- **Each resume decision is observable** via `log()` naming the ticket, the phase being skipped as
  already-persisted vs the phase being (re)entered, so an operator can see *why* a re-run did not
  recompute earlier phases (ref: Q5, Q13).
- **Optional, signature-blind single re-attempt on a bare `null` (secondary, behind a default-OFF
  flag).** Because no signature is available, a re-attempt cannot honor default-deny — it would
  also re-attempt a quota / dirty-tree `null`. It is therefore **opt-in, capped at exactly one
  extra attempt**, and explicitly documented as "cheap resilience that cannot distinguish
  transient from terminal." See Decision 2.
- **The pure resume/config logic has stdlib unit tests** in `scripts/*_test.py` (run by
  `run_tests.py`); suite stays green / CI passes (ref: Q11).
- **Non-resumable, non-transient behavior is unchanged** (fail-loud preserved): with both flags at
  their safe defaults the only behavior change is that a re-run does not recompute persisted
  upstream phases — which is the resilience the ticket asked for, with no signature inspection.

### Withdrawn from the prior draft (explicitly out of scope now)

The signature-based transient **classifier**, the **allowlist / default-deny** matching, the
**exponential backoff + jitter** schedule, and the **per-class mandatory-retry** behavior are all
**removed**. They are unbuildable at the `agent()` seam given the Probe Result. The corresponding
ACs (classifier / allowlist / default-deny) must be **rewritten on the ticket** to the
resume-centric ACs above before structure/plan proceed (flagged for the ticket owner).

## Delta (re-scoped)

- **New file** `scripts/qrspi_resilience_config.py` — pure resolvers (`resolve_resilience(cfg)`,
  `_bool_or`, `_pos_int_or`) + envelope emitter mirroring `qrspi_critics_config.py`; reads
  `.qrspi/config.json` via `qrspi_config.read_config`; emits always-complete
  `{ ok, resilience:{ resumeOnNull, singleReattempt, reattemptCap }, warnings }`.
- **New file** `scripts/qrspi_resilience_config_test.py` — auto-discovered by `run_tests.py`;
  covers config-present, config-absent (defaults), and malformed-block (warn + default) cases.
- **Modified** `.claude/workflows/qrspi-batch.js`:
  - Add `DEFAULT_RESILIENCE` lockstep constant + `readResilienceConfig()` worker +
    `parseResilienceEnvelope()` (mirrors `DEFAULT_CRITIC_PHASES`/`readCriticsConfig`/
    `parseCriticsEnvelope`), falling back to defaults on any parse failure.
  - Make the resume-skip decision **explicit and logged** at each phase entry: before (re)running a
    phase, consult the existing artifact-detection result and, when `resumeOnNull` is ON and the
    artifact is present + non-empty, `log()` "phase X already persisted — resuming past it" and
    skip the producer rather than recompute. (This formalizes the resolver's existing skip-if-exists
    behavior; the change is making it config-gated + observable, not inventing new persistence.)
  - **Optionally** (behind `singleReattempt`, default OFF) wrap the `agent()` call so a bare `null`
    triggers exactly one capped re-attempt before propagating `null` unchanged. No signature is
    read; no classifier is consulted. When the flag is OFF (default) this seam is a pass-through and
    behavior is byte-for-byte today's.
- **New** `.qrspi/config.example.json` `resilience` block documenting the defaults.

> The prior draft's `qrspi_transient_classifier.py`, `qrspi_backoff.py`, `qrspi_retry_config.py`
> and their tests, the `agentWithRetry` signature-classifying wrapper, and the sandbox-timer probe
> are **all dropped** — backoff/sleep is only relevant to multi-attempt timed retry, which is
> withdrawn. (A single re-attempt, if adopted, fires immediately with no backoff, so no timer
> primitive is needed and Decision 3 of the prior draft is moot.)

## Pattern Decisions

### Decision 1: Primary mechanism — resume-on-`null` vs classify-and-retry

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A (prior draft) | Classify a captured error signature against a transient allowlist, backoff-retry on match, default-deny | Honors the original AC wording | **Unbuildable** — the Probe Result shows the signature is a bare `null` at this seam, discarded before the script sees it. No input to classify. Rejected. |
| **B (chosen)** | **Resume-on-`null`: treat a mid-ticket abort as a checkpoint; do not recompute already-persisted upstream phases on the next pass; make the existing skip-if-exists resume explicit, config-gated, observable, and tested** | Delivers the ticket's real value ("resilient instead of all-or-nothing") with no signature; builds on already-committed artifact-detection; preserves fail-loud; fully unit-testable as pure config logic | Does not re-attempt the failed phase automatically — the operator/batch must re-run, but the re-run is cheap because prior phases are skipped. (Acceptable: batch is already idempotent and re-runnable.) |
| C | Push true transient-retry down to the harness layer where the signature exists | Correct layer for signature-based retry | **Out of this repo's reach** — the harness already does one retry below the seam; further work is a harness-team change, not a qrspi-batch change. Noted as the real home for any future signature retry. |

**Recommendation:** Option B.
**Rationale:** The reviewer's probe (Probe Result) makes A unbuildable and names B as "arguably the
real value behind this ticket." B reuses the repo's existing per-phase persistence + artifact
detection (ref: Q6, resolver) — it is the smallest change that delivers resilience, keeps the
load-bearing `null` contract intact (ref: Q1), and stays entirely in tested pure config logic
(ref: Q4, Q11). C is acknowledged as the correct long-term home for signature-based retry but is
outside this repo.
**NEW PATTERN?** No — it formalizes and config-gates the *existing* skip-if-exists resume; no new
exception path, no `try/catch` around `agent()`.

### Decision 2: Optional signature-blind single re-attempt (default OFF)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | No automatic re-attempt — resume only (Decision 1B alone) | Simplest; fully honors "leave the ticket untouched" semantics; zero risk of re-burning a terminal failure | A genuinely transient `null` still needs an external re-run to retry the failed phase |
| **B (chosen, behind a default-OFF flag)** | On a bare `null`, optionally re-attempt the same `agent()` call **exactly once** (hard cap, no backoff), then propagate `null` unchanged | Cheap resilience for the common single-blip case; the resume from Decision 1 still covers everything upstream | Cannot honor default-deny (no signature) — it also re-attempts quota/dirty-tree `null` once. Therefore **opt-in only**, capped at one, and documented as undiscriminating. |

**Recommendation:** Option B, **shipped default OFF** (`singleReattempt: false`).
**Rationale:** The probe rules out class-aware retry, so a re-attempt is necessarily signature-blind.
Making it opt-in + single-shot + uncapped-delay-free keeps the default behavior identical to today
(fail-loud) while giving operators a low-cost lever. The AC's "default-deny" requirement cannot be
met for re-attempt and **must be rewritten on the ticket** to "opt-in, signature-blind, single
re-attempt" — flagged.
**NEW PATTERN?** Partial — a single pass-through re-call of `agent()` on `null` is new, but it adds
no exception path and no classifier; when the flag is OFF it is inert.

### Decision 3: Where the (small remaining) logic lives

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **A (chosen)** | Config resolution + the resume/skip predicate in a tested Python module; JS is thin glue with a lockstep defaults mirror | Matches Functional-Core/Imperative-Shell mandate; CI-gated (ref: Q4, Q11, Q12) | One worker-agent call to read config at run start (already the pattern for `critics`) |
| B | Inline the config + predicate in JS | No extra spawn | Untestable harness-coupled JS (ref: Q12); violates the repo architecture |

**Recommendation:** Option A.
**Rationale:** Directly mirrors the `critics` config + lockstep-mirror pattern (ref: Q4). The only
deterministic logic left after the re-scope is config resolution and a simple
"artifact present + non-empty ⇒ skip" predicate, both of which belong in Python with `_test.py`
siblings.
**NEW PATTERN?** No — mirrors `readCriticsConfig`/`parseCriticsEnvelope` exactly.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| The ticket's ACs (classifier / allowlist / default-deny) no longer match the buildable design | high | med | **Rewrite the ACs on the ticket** to the resume-centric Desired End State BEFORE structure/plan; this design names that explicitly (Desired End State → Withdrawn) |
| Resume skips a phase whose persisted artifact is actually stale (e.g. an upstream reset left a leftover) | low | med | Reuse the existing `git clean`/reset discard hygiene (resolver + reset path already remove stale downstream artifacts, ref: Q6); resume only trusts artifacts the artifact-detection envelope reports present |
| Optional single re-attempt re-burns a terminal failure (quota/dirty-tree) once | low (flag default OFF) | low | Ship `singleReattempt` default OFF; hard cap of exactly one; documented as signature-blind |
| JS defaults mirror drifts from the Python `resilience` config authority | med | med | Keep the JS `DEFAULT_RESILIENCE` mirror in lockstep (comment as `DEFAULT_CRITIC_PHASES` does); cover with a contract fixture once that infra exists (ref: Q4, Q12) |
| Signature-based transient retry is still genuinely wanted | low | low | Documented as Decision 1 Option C — it belongs in the harness layer (which already retries once), not this repo; out of scope here, recorded for a future harness ticket |

## Open Questions

- OQ1: **RESOLVED** by the Probe Result above — API/network-layer `agent()` failures return a bare
  `null` with the signature discarded; only client-side config validation throws. This invalidated
  the signature classifier and drove the re-scope to resume-on-`null`.
- OQ2 (sandbox `setTimeout`/`Promise`): **MOOT / withdrawn** — backoff timing only mattered for
  multi-attempt timed retry, which is dropped. A single re-attempt (Decision 2) fires immediately
  with no delay, so no timer primitive is needed.
- OQ3 (`retry.enabled` default): **REPLACED** — the relevant default is `resumeOnNull` (proposed
  default ON, the resilience baseline) and `singleReattempt` (proposed default OFF, since it cannot
  honor default-deny). Confirm both defaults with the ticket owner when rewriting the ACs.
- OQ4 (trunk-sync `throw` in the deny-list): **RESOLVED / out of reach** — those throws travel a
  run-level path that never reaches the `agent()` seam, and with no classifier there is no deny-list
  to place them in. Out of scope; recorded for completeness.
