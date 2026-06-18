# Design — Structured phase-gate event log: systematic logging for the qrspi review-gate pipeline

**Ticket:** RUS-86
**Research basis:** research.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Current State

There is no structured per-phase event emission today; transitions surface only via two harness-injected globals, `phase('<Label>')` (UI phase declaration) and `log('<freeform>')` (human progress), neither defined in the file (ref: Q1). The per-ticket loop runs `resolveTicket → ensureRestacked → switch(r.decision.action)` dispatching to `doDesign/doPlan/doImplementation/doSubmit/doReset/doRevise/doLand/skip`, and at dispatch time `t.id`, `r.decision.{action,phase,nextPhase,reason,ciFailing,changeRequested}` are in scope as natural emission data (ref: Q1). A module-level `runId` is computed once (env `QRSPI_RUN_ID` → `crypto.randomUUID()` → crypto-hex → `'run-fallback'`), never `Date.now()`/`Math.random()`, and is a free `const` readable anywhere in the loop without threading (ref: Q2). There is no span/span_id concept anywhere — only per-step `label` strings; any nesting is structural function-call depth, not an id, so span ids must be minted net-new the same crypto way as `runId` (ref: Q3).

Shared Python helpers are stdlib-only, self-locating, and emit a single JSON envelope on stdout; two self-location idioms exist — `Path(__file__).resolve().parents[1]` for invoked-checkout config reads, and `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` (git-common-dir first) for artifacts that must land in the MAIN checkout (ref: Q4). The orchestrator never execs Python directly; a thin worker agent runs an exact verbatim command and returns the script's JSON stdout, parsed either via a StructuredOutput `schema` or `JSON.parse` — so any non-JSON on stdout breaks parsing, and there is no `cli.log` or stderr-routing convention today (ref: Q5). `qrspi_config.py` reads ONE top-level key via `select_value` (no dot-path, truthy-or-default); it supports neither a nested `observability.*` block nor the top-level `ciReviseBackoffBase`/`ciReviseBackoffCap` keys, none of which exist in `.qrspi/config.example.json` (ref: Q6). The nested `critics.*` block is read by a separate `qrspi_critics_config.py`, the established precedent for nested-block reads (ref: Q6).

`qrspi_cleanup.py` destroys a merged ticket's worktree via `git worktree remove --force <root>/.worktrees/<id>`, so anything under `.worktrees/<id>/.qrspi/<id>/` (including the critic-metrics ledger) is destroyed at teardown; the main-checkout `.qrspi/` survives (ref: Q7). The `CI-Revise-Attempt` trailer is parsed (not written) by the gather via a MULTILINE last-occurrence regex, exposed as `ciReviseAttempt` and force-reset to 0 whenever CI is not red; it is written `+1` by `qrspi_ci_revise_bump.py`. Crucially, `committedDate` DOES NOT EXIST — the GraphQL `commits(last:1)` selection carries no head-commit timestamp and `build_state` exposes none (ref: Q8). The CI cap is evaluated in resolver step 2c, after the unified-feedback handler and before the active-phase block, operating only on the frontier: red → `revise` if `attempt < ci_revise_cap` else `wait (ciGaveUp)`, pending → `wait`, green/none falls through; `ci_revise_cap` is a default-arg passed in, the resolver does no disk read (ref: Q9). `resolve()` is a pure function importing only `argparse/json/sys` — no clock, no time access, no injection seam — but it already injects `ci_revise_cap=3` as a default-arg, the exact pattern to mirror for an injected clock (ref: Q10).

The resolver's machine phase vocabulary is exactly `["design","plan","implementation"]` (singular machine value is `implementation`, NOT `implement`, though the agentType is `qrspi-implement` and the UI label is Title-Case); no `actor` field exists anywhere, so its vocabulary is net-new (ref: Q11). The metrics ledger is the canonical fail-CLOSED sink: it verifies a non-empty write and exits non-zero on failure, `&&`-chained so a failed append fails the step; the deliberate fail-OPEN inversion wraps every fs op in try/except, swallows, never raises, and is never `&&`-gated, with `parseCriticPhasesEnvelope`'s swallow-and-continue as in-repo precedent (ref: Q12). Tests are stdlib-only assert-based `scripts/*_test.py` siblings auto-discovered by `run_tests.py` (exit 0/non-zero contract, 180s timeout), the CI gate (ref: Q13). There is no `.qrspi/observability/` writer, no structured event log, no Python `logging` usage, and no `events.schema.json` — the logger is built net-new (ref: Q14). All JSON validation is hand-rolled: a module-level `frozenset` of valid values plus a membership check raising `ValueError` (fail-closed), or best-effort-default (fail-open); no enum is loaded from a shared schema file today (ref: Q15).

## Desired End State

| Acceptance criterion | System behavior |
|---|---|
| Phase-gate events for every phase, correct `event_type`/`status`, canonical phases | `qrspi-batch.js` emits `phase_start`/`phase_end`/`phase_success`/`phase_failure`/`phase_skip` around each `do*` dispatch, passing lowercase `design`/`plan`/`implementation` from `r.decision.phase` (ref: Q1, Q11). |
| Append-only, append-aligned, one JSON line, per-ticket in main checkout, flush+fsync | A new `qrspi_event_log.py` appends one `json.dumps(event)+"\n"` per call, `flush()`+`os.fsync()` each write, to `<main_root>/.qrspi/observability/<ticket>.events.jsonl` resolved via `qrspi_paths.resolve_repo_root` so it survives `qrspi_cleanup.py` (ref: Q4, Q7). |
| `parent_span_id` caller-supplied and correctly nested; test asserts nesting | The emitter accepts `parent_span_id` as an argument (never invents it); the orchestrator mints a phase `span_id` (root → `null`), then passes that id as `parent_span_id` on critic/retry/command events; a unit test asserts a nested event's `parent_span_id` equals the phase `span_id` (ref: Q3). |
| Every error → `error` event with `message` + `error_code` | Error paths emit `event_type=error`, `status=error`, with `error_code` and optional `traceback` in `context` (ref: Q12). |
| Every retry → `retry` + `error_retry` with `retry_attempt` + `backoff_seconds` | The revise path emits a `retry` event and an `error_retry` event carrying numeric `retry_attempt` and the enforced `backoff_seconds` in `context` (ref: Q9). |
| CI-revise backoff gates revises; injected-clock unit test | A new pure backoff gate in `resolve()` defers a still-red frontier to `wait` until `min(base·2^(attempt-1), cap)` seconds elapsed since head-commit `committedDate`, then `revise`; `now` and the backoff config are injected default-args; `committedDate` is added to GraphQL + `build_state` (ref: Q8, Q9, Q10). |
| Log rotation at configurable size, collision-free archive names | `qrspi_log_rotate.py` rolls a per-ticket file at `observability.logSizeThreshold` (default 10 MB), gzips it to `.qrspi/observability/archive/` with a collision-free name (ref: Q7, Q12). |
| Retention cleanup archives then removes old files | `qrspi_log_retention.py` compresses+archives+removes per-ticket files older than `observability.logRetentionDays` (default 30) (ref: Q7). |
| CLI structured logging + chosen `cli.log` contention strategy, tested | The shared logger writes structured JSON to `cli.log`; the orchestrator is the first adopter; the chosen contention strategy is implemented and tested for no torn lines (ref: Q5, Decision 4). |
| Log level filtering | The logger drops records below the active level (`QRSPI_LOG_LEVEL` env → `observability.logLevel` config → `info` default) (ref: Q6). |
| Fail-open verified; stdout stays clean | Forced write/flush/fsync failure in emitter and CLI logger returns success, never raises/halts; all log output goes to file/stderr, never stdout (ref: Q5, Q12). |
| Unit tests for emitter, rotator, retention | Each ships a `scripts/*_test.py` sibling auto-discovered by `run_tests.py` (ref: Q13). |
| `events.schema.json` is the single source of truth for enums | A new `.qrspi/observability/events.schema.json` holds the `event_type`/`status`/`phase` enums; the validator loads them at runtime rather than re-hardcoding a `frozenset` (ref: Q15). |

## Delta

New files: `scripts/qrspi_event_log.py` (emitter + hand-rolled validator), `scripts/qrspi_event_log_test.py`; `scripts/qrspi_cli_logger.py` (CLI structured logger + level filter + contention strategy), `scripts/qrspi_cli_logger_test.py`; `scripts/qrspi_log_rotate.py` + `_test.py`; `scripts/qrspi_log_retention.py` + `_test.py`; `scripts/qrspi_observability_config.py` (nested `observability.*` reader, mirroring `qrspi_critics_config.py`) + `_test.py`; `.qrspi/observability/events.schema.json` (committed enum source of truth); `scripts/qrspi_backoff.py` (pure backoff policy) + `_test.py` (or fold the pure function into the resolver — see Decision 5).

Modified files: `scripts/qrspi_pr_state.py` — add `committedDate` to the `commits(last:1)` GraphQL selection and to `build_state`'s per-phase output (additive, mirroring `mergedAt`) (ref: Q8). `scripts/qrspi_resolve_state.py` — add `now=None` and backoff config default-args to `resolve()`, insert the backoff gate in step 2c relative to the existing cap (ref: Q9, Q10). `scripts/qrspi_resolve.py` — read `ciReviseBackoffBase`/`ciReviseBackoffCap` and thread them (plus a real `now`) into `resolve()`, like it already threads `ciReviseCap`. `.claude/workflows/qrspi-batch.js` — wire emit calls around each `do*` dispatch and the critic/revise paths via verbatim worker shell-outs (Q5 worker-parse path; never `&&`-gated, Q12). `.qrspi/config.example.json` — add the `observability.*` block and the two top-level backoff keys (ref: Q6). `scripts/run_tests.py` auto-discovers the new `_test.py` files (no change needed) (ref: Q13).

## Pattern Decisions

### Decision 1: Event-log location and self-location idiom

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Write to MAIN checkout via `qrspi_paths.resolve_repo_root(validate=False)` | Survives `qrspi_cleanup.py` teardown; matches the metrics-append/cleanup idiom | Two-flavor self-location must be chosen correctly |
| B | Write under worktree `.qrspi/<id>/` like the metrics ledger | Simplest, mirrors nearest sink | Destroyed at teardown — violates the survival AC |

**Recommendation:** Option A
**Rationale:** AC requires survival of worktree teardown; only the git-common-dir resolver lands in the main checkout (ref: Q4, Q7). Option B is the exact trap the metrics ledger fell into (ref: Q7).
**NEW PATTERN?** No — reuses `qrspi_metrics_append.py`/`qrspi_cleanup.py` self-location (ref: Q4).

### Decision 2: Enum source of truth

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Validator loads enums from `events.schema.json` at runtime | Single source of truth (AC); JS + Python agree | New convention; file-read on a fail-open path |
| B | Hard-code a `frozenset` per module as today | Matches current idiom (ref: Q15) | Re-hardcodes enums — violates the AC; drift risk (ref: Inconsistencies, design.md:76 drift) |

**Recommendation:** Option A
**Rationale:** AC explicitly names `events.schema.json` as the single source of truth; keep the in-Python membership-check + `ValueError` idiom but derive the set from the loaded file (ref: Q15). Best-effort `read_config`-style load applies (ref: Q15).
**NEW PATTERN?** Yes — no shared schema file exists today; enums are per-module frozensets (ref: Q15). Justified because the AC mandates it and two languages must share one enum set.

### Decision 3: Fault posture of emitter/logger

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Fail-OPEN: try/except every fs op, swallow, never raise, never `&&`-gate | Observability never halts work (AC); matches `parseCriticPhasesEnvelope` (ref: Q12) | Silent loss of a log line on disk failure |
| B | Fail-CLOSED like the metrics ledger | Guaranteed durability | Halts the pipeline on a telemetry write — violates fail-open AC |

**Recommendation:** Option A
**Rationale:** The AC mandates the deliberate opposite of the fail-closed ledger; the JS side must NOT `&&`-chain the emitter into a gating command (ref: Q12).
**NEW PATTERN?** No — fail-open precedent exists (`parseCriticPhasesEnvelope`) (ref: Q12).

### Decision 4: `cli.log` contention strategy

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Per-run file `cli.<run_id>.log`, merged-on-read | Mirrors the per-ticket event-log split; no lock; `runId` already available (ref: Q2) | Many small files; merge-on-read consumer needed |
| B | Atomic `O_APPEND` with a hard per-line cap below `PIPE_BUF` | Single file; POSIX-atomic for small lines | Fragile if a line exceeds the cap; the AC requires the cap be enforced+tested |

**Recommendation:** Option A
**Rationale:** The event log already justifies a per-writer split with no lock under the single-writer-per-stream invariant; `cli.log` lacks per-ticket isolation, so reusing the per-run split is the lowest-risk parallel to the event-log design and reuses the existing `runId` (ref: Q2, Q5). The AC explicitly permits either; A avoids the `PIPE_BUF` line-size hazard.
**NEW PATTERN?** No — same split-and-merge approach as the per-ticket event log.

### Decision 5: Where the backoff policy lives + clock injection

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Pure `should_revise_now(attempt, committed_date, now, base, cap)` as a default-arg in `resolve()` | Keeps resolver pure+disk-free; mirrors `ci_revise_cap` injection; unit-testable with injected `now` (ref: Q10) | Adds params to `resolve()` |
| B | Compute backoff at the JS orchestrator before calling the resolver | Keeps resolver untouched | JS is not unit-testable (ref: Q13); violates the "unit-tested in the resolver with an injected clock" AC |

**Recommendation:** Option A
**Rationale:** The AC requires the backoff be unit-tested in the resolver with an injected clock; `resolve()` already injects `ci_revise_cap` as a default-arg, the exact seam to extend with `now`/`base`/`cap` while staying pure (ref: Q9, Q10). The gate sits in step 2c governing the red frontier, before the cap converts red→wait, so backoff defers within the cap window (ref: Q9). `committedDate` must first be added to the gather (ref: Q8).
**NEW PATTERN?** No — extends the existing default-arg injection seam (ref: Q10).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| A log line escapes to stdout, breaking the worker `JSON.parse` of an envelope | med | high | Emitter/logger write ONLY to file (or stderr); the verbatim worker command must not let the logger touch stdout; assert "stdout stays clean" in tests (ref: Q5, fail-open AC). |
| `committedDate` added to GraphQL/`build_state` regresses the gather or its consumers | med | med | Additive-only, mirror `mergedAt` exactly; null-safe default when absent so the backoff degrades to "no defer" (ref: Q8). |
| Backoff gate is a no-op in practice (only defers within a pass, no wake-up) | high | low | Documented activation regime: only bites under a tight loop/fast cron; defaults (300s/3600s) chosen with that in mind; acceptable per ticket scope (ref: Q9, ticket activation-regime note). |
| `events.schema.json` file-load on a fail-open path fails, leaving no enums | low | med | Best-effort load with a safe in-code fallback set; never raise; keep validation fail-open consistent with Decision 3 (ref: Q12, Q15). |
| Nested `observability.*` config read diverges from `qrspi_config.py` single-key reader | med | med | New `qrspi_observability_config.py` mirrors `qrspi_critics_config.py` exactly; do not extend the single-key `qrspi_config.py`; env `QRSPI_LOG_LEVEL` overrides config (ref: Q6). |
| Phase enum diverges (`implement` vs `implementation`, Title-Case UI labels) | med | high | Schema `phase` enum copies the resolver's lowercase machine set verbatim; a test pins it (ref: Q11). |

## Open Questions

- OQ1: Confirm the merged-on-read consumer scope — the ticket says the per-ticket event stream is "presented as a single merged-on-read stream" and `cli.<run_id>.log` is merged-on-read, but no reader/tool is named. Is a read/merge CLI in scope for RUS-86, or deferred to the RUS-85 follow-up?
- OQ2: Confirm `cli.log` strategy choice (Decision 4 Option A per-run split vs Option B atomic-append). The AC accepts either; pick before structure.
- OQ3: Should the pure backoff policy live in the resolver module or a separate `qrspi_backoff.py` imported by it (Decision 5)? Both satisfy the injected-clock AC; the split affects test placement.
- OQ4: Default `actor` values are net-new (ref: Q11). Confirm the vocabulary: agentType for agent transitions, `batch` for orchestrator decisions, `cli` for standalone scripts, `user` for human actions — as the ticket states. Lock this into `events.schema.json`?
