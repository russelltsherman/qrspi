# Design — Structured phase-gate event log: systematic logging for the qrspi review-gate pipeline

**Ticket:** RUS-86
**Research basis:** research.md @ 2026-06-18T21:35:00Z
**Generated:** 2026-06-18T22:00:00Z
**Status:** draft

## Current State

The orchestrator (`.claude/workflows/qrspi-batch.js`) has no structured event log today. Its only telemetry is harness-injected `log()` run-log lines (human-readable, no structured fields, no file the design controls), a best-effort Linear status projection, and a fail-closed critic-metrics ledger that is not wired into the live autonomous batch (ref: Q15). There is no span/trace concept anywhere in the codebase — searches for `span_id`/`parent_span_id`/`traceId` returned nothing; nesting is expressed purely as JS call structure, and the only correlation handle is the `label` string `<action>:<ticket>#<index>` (ref: Q3).

Phase transitions pass through three seam points: the harness-injected `phase(label)` global at each handler entry, the per-ticket dispatch `switch` (lines 1644-1662) inside a `try/catch` that already isolates per-ticket, and `runPhase` (lines 512-532), the per-artifact boundary with natural start/success/failure returns (ref: Q1). At those points `t.id` (ticket), the literal `phase`/`agentType` strings, and `s.n` (slice) are all in scope, but there is **no `runId`** in the workflow file — the only `runId` producer is the unused metrics path, and a prior attempt to mint one used the forbidden `Date.now()`/`Math.random()` (ref: Q2).

The JS sandbox cannot run python/git/gh; every side-effecting capability is a self-locating `scripts/qrspi_*.py` invoked by a worker `agent()` told to run one verbatim command and return a single stdout JSON envelope, parsed in JS via `extractJsonObject` (outermost balanced object) (ref: Q5, Q12). The config reader supports only a single flat top-level key — it cannot read `observability.*` as a dot-path, and JS `parseConfigEnvelope` outright rejects non-string (object) envelope values (ref: Q4). The `CI-Revise-Attempt` trailer is parsed and read-side-zeroed when CI is not red, but `committedDate` is never gathered (the GraphQL query omits it) and `ciReviseAttempt` is computed internally yet not re-emitted at the resolver envelope top level (ref: Q6, Q9). The resolver evaluates CI in slot 2c (after unified-feedback, before active-phase) on the frontier (ref: Q10). `qrspi_cleanup.py` destroys only `.worktrees/<id>` + branches + origin refs and never touches the main checkout's `.qrspi/` (ref: Q8). Existing write scripts auto-create parents via `makedirs(exist_ok=True)`, verify non-empty, and are fail-closed; no `flush`/`fsync` call exists anywhere (ref: Q11, Q15). The established test pattern is stdlib `unittest`, time/failure injected as a plain function argument, filesystem tested against a `TemporaryDirectory` with monkeypatched `resolve_repo_root` (ref: Q14).

## Desired End State

Maps each acceptance criterion to system behavior:

- **Phase-gate events for every phase, correct `event_type`/`status`, canonical `phase` values.** A new `scripts/qrspi_event_emit.py` writes one JSONL event per transition; the orchestrator calls it at `runPhase` boundaries and dispatch points. `phase` is constrained to `["design","plan","implementation"]` (plus reserved values) matching `PHASES` in the resolver (ref: Q7).
- **Append-only, one line per event, per-ticket, in main checkout, with `flush()`+`os.fsync()`.** The emitter opens `<main-root>/.qrspi/observability/<ticket_id>.events.jsonl` (root resolved via `qrspi_paths.resolve_repo_root`, NOT under `.worktrees/`, so it survives teardown), appends one JSON line, then `flush()`+`fsync()` (ref: Q8, Q11).
- **Caller-supplied, correctly-nested `parent_span_id`.** Span ids are minted and threaded by the orchestrator: a phase span is a root (`parent_span_id=null`); nested critic/retry/command events carry the phase's `span_id`. A test asserts a nested event's `parent_span_id` equals its enclosing phase `span_id`.
- **Every error → `error` event with `message`+`error_code`; every retry → `retry`+`error_retry` with `retry_attempt`+`backoff_seconds`.** The emitter accepts these fields in `context`; the orchestrator emits them on its failure/CI-revise paths.
- **CI-revise backoff gates revises.** A pure backoff helper computes `min(base·2^(attempt-1), cap)`; the resolver, in slot 2c on the `red` branch, returns `wait` if `now - committedDate < window` (else `revise`), preserving the at-cap→`wait`+`ciGaveUp` terminal. `committedDate` is added to the GraphQL query and threaded through; `ciReviseAttempt` gains a re-emit helper; backoff is config-driven (`ciReviseBackoffBase`/`ciReviseBackoffCap`) and unit-tested with an injected clock (ref: Q6, Q9, Q10).
- **Rotation + retention.** A `scripts/qrspi_log_rotate.py` rolls a per-ticket file at `logSizeThreshold`, compresses old files with collision-free archive names into `.qrspi/observability/archive/`, and removes files older than `logRetentionDays`.
- **CLI structured logging.** A shared importable logger module emits JSON to `cli.log` and optionally to **stderr** (never stdout) at the configured level; the orchestrator is the first adopter; the chosen `cli.log` contention strategy is implemented and tested.
- **Log-level filtering; fail-open verified; unit tests for emitter/rotator/retention; `events.schema.json` as single source of truth** for the `event_type`/`status`/`phase` enums, loaded by a stdlib hand-rolled validator.

## Delta

New files: `scripts/qrspi_event_emit.py` (emitter CLI + pure helpers) and `_test.py`; `scripts/qrspi_logger.py` (shared importable CLI logger) and `_test.py`; `scripts/qrspi_log_rotate.py` (rotation + retention) and `_test.py`; `scripts/qrspi_backoff.py` (pure backoff helper) and `_test.py`; `.qrspi/observability/events.schema.json` (enum source of truth). New config block `observability.*` documented in `.qrspi/config.example.json`, plus top-level `ciReviseBackoffBase`/`ciReviseBackoffCap`.

Modified files: `scripts/qrspi_pr_state.py` — add `committedDate` to the GraphQL commit selection and thread it through `parse_pr_nodes`. `scripts/qrspi_resolve_state.py` — slot the backoff `wait` deferral into step 2c on the `red` branch (consume `committedDate`+`attempt`+`base`+`cap`+injected `now`). `scripts/qrspi_resolve.py` — add a `ci_revise_attempt`/`committedDate` re-emit helper to `build_envelope`; read the new backoff config keys. `scripts/qrspi_config.py` — add nested whole-object read for `observability` (whole-object via `--key observability`, sub-parsed in the consumer — avoids touching the JS string-only path). `.claude/workflows/qrspi-batch.js` — mint a `runId` and per-phase `span_id`; thread parent span ids; add `doEmit()` worker helper + `parseEmitEnvelope`; call it at `runPhase`/dispatch/error/CI-revise boundaries; consume the re-emitted backoff fields.

## Pattern Decisions

### Decision 1: Failure posture of the event emitter and CLI logger

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Fail-CLOSED (persist/metrics precedent): verify non-empty, return `ok:false`, exit 1 | Reuses existing write-verify code; loud on failure | Violates ticket's explicit fail-OPEN mandate; a logging failure would halt observed work |
| B | Fail-OPEN (Linear/read-side precedent): wrap `makedirs`+`open`+write+`flush`/`fsync` in try/except, WARN, return `ok:true` | Matches ticket mandate; mirrors the best-effort Linear projection; observability never blocks work | Departs from the persist/append fail-closed precedent; silent data loss possible on disk failure |

**Recommendation:** Option B
**Rationale:** The ticket explicitly mandates fail-OPEN as the deliberate opposite of the fail-closed metrics ledger. Research confirms two coexisting stances and that the Linear projection's "WARN and continue, never block real work" is the precedent to mirror (ref: Q15, Q11). The emitter still returns a structured envelope (the triad contract) but never raises.
**NEW PATTERN?** Yes — a fail-OPEN write helper is net-new (no `flush`/`fsync` exists today, ref: Q15); justified because the existing write helpers are fail-closed and the ticket requires the opposite for telemetry.

### Decision 2: `runId` and `span_id` minting under the no-`Date.now()`/no-`Math.random()` rule

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Mint ids in JS with `crypto.randomUUID()` | Single source in orchestrator | Project memory records a prior `Date.now()`/`Math.random()` fallback bug when `crypto.randomUUID` was absent; harness cached-snapshot regeneration risk (ref: Q2) |
| B | Mint ids inside the python emitter (`uuid4`) and return them in the envelope; JS threads the returned `span_id` as the parent of nested events | Keeps `uuid4` in the impure CLI (the established injectable pattern); JS does no nondeterministic work | Requires a round-trip: phase-start emit returns the `span_id` JS must hold and pass down |

**Recommendation:** Option B
**Rationale:** The emitter is already a python CLI where `uuid4`/`datetime.now()` legitimately live in the impure `main` (the functional-core/imperative-shell pattern, ref: Q14). Returning `event_id`/`span_id` in the stdout envelope lets JS thread parent ids without itself calling forbidden nondeterministic APIs (ref: Q2). `runId` is minted once per run by the same mechanism (a `qrspi_event_emit.py --new-run` call, or derived from the first phase emit) and carried in `context.run_id`.
**NEW PATTERN?** Yes — span/trace identity is entirely net-new (ref: Q3); justified because no correlation handle beyond the `label` string exists.

### Decision 3: `cli.log` contention strategy

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Per-run file `cli.<run_id>.log`, merged-on-read | Mirrors the per-ticket event-log split; no cross-process interleave; reuses the no-lock argument | More files; merge-on-read tooling needed; `run_id` must be in scope at every CLI log call |
| B | Single shared `cli.log` with `O_APPEND` + hard per-line size cap below `PIPE_BUF` | One file; POSIX atomic-append for small writes | Atomicity only holds below `PIPE_BUF`; no cross-process ordering; a long line tears (ref: Q13) |

**Recommendation:** Option A
**Rationale:** Research is explicit that the per-ticket no-lock argument does NOT extend to `cli.log`, and that concurrent batch/`/qrspi-work`/`/review-*` runs have no lock/PID/mutex guard (ref: Q13). A per-run file confines each writer to its own file exactly as the per-ticket event log does, sidestepping the torn-line risk entirely. The default `observability.cliLog` path becomes the merged-read base; actual writes go to `cli.<run_id>.log`.
**NEW PATTERN?** No — it directly reuses the per-ticket-split, merged-on-read pattern the event log already establishes.

### Decision 4: Reading the nested `observability.*` config block

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add dot-path support to `qrspi_config.py` `select_value` | General; future nested keys work | Larger blast radius; JS `parseConfigEnvelope` still rejects object values, so JS-side nested reads stay broken |
| B | Read the whole `observability` object via `--key observability` in python consumers only; sub-parse there; keep JS on flat string keys | Minimal change; python emitter/rotator own their paths (the model never types `observability.*`) | JS cannot read `observability.*` directly — but JS never needs to (the python scripts own those paths) |

**Recommendation:** Option B
**Rationale:** The emitter, rotator, and logger are python scripts that self-own their `.qrspi/observability/` paths (the token-free-staging rationale: let the script own the qrspi-laden path, ref: Q4, Discovered Patterns). JS only needs the flat top-level backoff keys (`ciReviseBackoffBase`/`ciReviseBackoffCap`), which it already can read as strings. This avoids the documented JS object-rejection constraint entirely (ref: Q4).
**NEW PATTERN?** No — whole-object read via the existing single-key CLI is within current capability; consumer-side sub-parse is conventional.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Concurrent runs (batch + `/qrspi-work` + `/review-*`) write the same `<ticket>.events.jsonl` with no lock | med | med | Per-ticket file confines damage to one ticket; append+`fsync` keeps each line intact; document that cross-run ordering is best-effort, not guaranteed (ref: Q13) |
| A JSON-shaped stderr log line precedes the script's stdout envelope and `extractJsonObject` grabs it first | med | high | Logger emits only NON-JSON-shaped lines to stderr; scripts emit the envelope as the sole/outermost `{...}`; the emit worker prompt returns only stdout (ref: Q12) |
| `runId`/`span_id` minting reintroduces a forbidden `Date.now()`/`Math.random()` path | med | high | Mint all ids in the python emitter (`uuid4`) per Decision 2; assert no nondeterministic API in JS (ref: Q2) |
| Backoff timing diverges from / double-counts the `CI-Revise-Attempt` cap counter | med | high | Derive `retry_attempt` from the SAME trailer via `ci_revise_attempt`; backoff only adds a `wait` deferral, never increments the trailer (orchestrator's `bumpCiReviseTrailers` stays sole increment authority) (ref: Q6, Q9) |
| Backoff is a no-op in practice because the gate only defers within a pass, never schedules a wake-up | high | low | Documented expected behavior per ticket: gate only bites under a tight loop/fast cron; defaults chosen accordingly — surface in Open Questions |
| Fail-open emitter silently loses events on a real disk/permission failure | low | med | WARN on each swallowed failure so loss is observable in the run log; rotation/retention bound disk growth (ref: Q11, Q15) |

## Open Questions

- OQ1: Should `runId` be minted once per batch invocation (one id across all tickets in a run) or once per ticket-step? The metrics precedent treats `runId` as per-invocation; confirm the intended granularity for `context.run_id`.
- OQ2: Given the backoff gate only defers within a resolver pass (no scheduled wake-up), is the intended operating regime a tight loop / fast cron, and what default `ciReviseBackoffBase`/`ciReviseBackoffCap` values fit that cadence (ticket defaults 300s/3600s)?
- OQ3: For `cli.log` per-run files, what is the merge-on-read consumer — is a reader tool in scope for this ticket, or is on-disk per-run JSONL sufficient for now?
- OQ4: Should `committedDate` use the head commit's `committedDate` or `authoredDate` when an amend rewrites the timestamp? Amends (the CI-revise path) rewrite the commit, which affects the elapsed-time measurement.
