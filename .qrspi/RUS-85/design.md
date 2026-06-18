# Design — Structured phase-gate event log (systematic logging)

**Ticket:** RUS-85
**Research basis:** research.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft (open questions resolved in design review 2026-06-18 — see Resolved Decisions)

## Current State

The phase pipeline has no operational observability. Phase transitions are driven entirely by `.claude/workflows/qrspi-batch.js`; there is no central Python state machine — `qrspi_resolve_state.py` only *decides* the next action while the JS shell *executes* the transition (ref: Q1). The single chokepoint for planning-artifact transitions is `runPhase()` (qrspi-batch.js:512-532), the coarse per-action dispatch is the `switch (a)` block (qrspi-batch.js:1644-1662), and per-ticket success/failure terminates in the surrounding `try/catch` (ref: Q1, Q9).

Correlation context is already threaded without re-derivation: `ticket_id` is the ticket object `t.id` (format `RUS-N`) passed through every call, and `phase` is carried both as a human label argument and authoritatively as `r.decision.phase` / `r.decision.nextPhase` on the resolver envelope (ref: Q2). The artifact set is fixed: `["questions","research","design","structure","plan","worktree"]`, and PR-gated phases collapse to three: design / plan / implementation (ref: Q2).

Files under `.qrspi/<id>/` are written two ways: `qrspi_persist.py` (staging-plus-move for `.md` artifacts) and `qrspi_metrics_append.py`, which is the direct precedent for a JSONL event writer — it appends one JSON line per call to `<root>/.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`, creating the parent dir then verifying non-empty (ref: Q3). Both resolve the host checkout root via `qrspi_paths.resolve_repo_root` (git-common-dir first), so a path joined onto that root resolves against the **main checkout**, reachable from inside any worktree (ref: Q3). There is no `.qrspi/observability/` directory and no `events.jsonl` anywhere today; the only JSONL artifacts are per-ticket `critic-metrics.jsonl` files (ref: Q3, Q14). Those `.qrspi/<id>/*` artifacts are committable by default — `.gitignore` ignores only `config.json`, `features/`, `.worktrees/`, and a few others; there is no precedent for ignoring a generated log under `.qrspi/` (ref: Q14).

There is no shared logging module; the closest reusable primitive is `qrspi_metrics_append.append_line` (a JSONL-append-with-verify coupled to the critic ledger path), and `qrspi_paths.py` is the only true shared lib (ref: Q5). The dominant convention is each script printing exactly one JSON envelope to stdout and exiting 0/1, with human text going to stderr (ref: Q5, Q13). Config is read best-effort: `qrspi_config.read_config(repo_root)` returns `{}` on any error or non-dict JSON and never raises; integer settings like `ciReviseCap` deliberately bypass the string-only `--key` CLI and read the raw dict, then apply a pure `coerce_cap` that rejects non-positive / non-int / `bool` values to a documented default (ref: Q4, Q10).

Failure capture exists at two points, both in JS: the `runPhase` null/`!ok` sentinel (clean failure) and the per-ticket `try/catch` that records `{action:'errored', summary}` and continues to the next ticket (ref: Q9). The JS sandbox has no filesystem, `Date.now()`, or `Math.random()` (the documented runId bug), and the `agent()` seam discards error detail, surfacing only `null` (ref: Q1, Q7, Q9). The unit-test convention is stdlib-only `unittest`, one `scripts/<name>_test.py` sibling per script, auto-discovered by `scripts/run_tests.py` and gated in CI (ref: Q11).

Three ticket assumptions do not hold against the codebase. There is **no exponential-backoff policy** and **no `error_code` field** — the only retry-bounding mechanism is a linear consecutive-red counter (`CI-Revise-Attempt: N` trailer) plus a cap (default 3); failures surface as free-text strings (ref: Q6). There are **no `trace_id` / `span_id` / `parent_span_id` analogues** — the only correlation key is `t.id`, and the one historical `runId` is an orphaned consumer with no live producer (ref: Q7). The shared global `.qrspi/observability/events.jsonl` named in the ticket does not exist today (ref: Q3, Q8, Q14). The first two gaps are resolved by recording only real values (Decision 1 / Resolved Decisions OQ1); the third is **honored as written** by treating the event log as operational telemetry in the main checkout (Decision 2 / OQ2), which is a different category from the per-ticket committed artifacts and therefore does not violate per-ticket isolation.

## Desired End State

A new tested Python module emits structured phase-gate events as append-only JSONL to a single shared, gitignored log in the main checkout, mirroring the `qrspi_metrics_append.py` writer precedent, wired in at the existing transition points. Each ticket acceptance criterion maps as follows.

- **Every phase transition produces a structured event (start, end, success, failure, retry).** Events are emitted Python-side wherever a script already runs at the transition — phase *success* from `qrspi_persist.py` (it already runs at the persist gate), the *decision* event from `qrspi_resolve.py`, and the *richest failure* event from the failing script itself before its non-zero exit. Only the points where **no Python script runs** — the per-artifact *start* before `agent()`, the `agent()`→`null` sentinel, and the per-ticket thrown `catch` — emit a coarse event via a single best-effort JS→Python call (see Decision 1). This covers questions/research/design/structure/plan/worktree (via `runPhase`) and the coarse actions (via the dispatch `switch`) (ref: Q1, Q9).
- **Events append to a single JSONL file; append-only, never rewritten, crash-safe.** One shared file `<main-root>/.qrspi/observability/events.jsonl` (Decision 2). Writes use a single atomic append per line — `os.open(path, O_APPEND|O_WRONLY|O_CREAT)` then one `os.write()` of `json.dumps(line)+"\n"` (each event guarded under PIPE_BUF, ~4 KiB) — with a post-write non-empty verify and fail-closed `ok:false` on any error, the established crash-safety posture extended for the shared target (ref: Q3, Q8).
- **Standard event schema** (`event_id`, `trace_id`, `span_id`, `parent_span_id`, `timestamp`, `event_type`, `ticket_id`, `phase`, `actor`, `status`, `message`, `context`). `ticket_id` and `phase` reuse already-passed values (ref: Q2); `timestamp` is Python `datetime.now(timezone.utc).isoformat()` — the allowed source, not JS (ref: Q7). Correlation IDs are generated entirely Python-side (Decision 3): `trace_id = uuid5(NAMESPACE, ticket_id)` (deterministic, no time/random), `span_id` / `event_id` = `uuid4()`, `parent_span_id` threaded from JS where phase nesting is known.
- **Error and retry tracking with failure message, error code, and backoff duration.** Failure message is captured from the available source (Python script text, or the JS `catch` summary). `error_code` and `backoff_duration` have **no existing source** (ref: Q6) and are therefore **omitted** rather than fabricated; retry events record the real `CI-Revise-Attempt` count from the existing trailer in `context` (Resolved Decisions OQ1).
- **Retry intervals follow the exponential-backoff policy in pipeline config.** No such policy exists in the review-gate pipeline (the only `backoff` in the repo is `grade.py`'s unrelated LLM-judge retry) (ref: Q6). This requirement is **descoped** (OQ1): the design records retry *events* keyed to the real `CI-Revise-Attempt` counter and does not fabricate a backoff schedule. Adding a real backoff policy is deferred to a separate ticket.
- **Log rotation at configurable size (default 10 MiB); retention configurable (default 30 days); old files compressed and archived.** New settings read via `read_config` + dedicated `coerce_*` functions (default `10*1024*1024` bytes, default 30 days), mirroring `coerce_cap` semantics — reject non-positive / non-int / `bool` to the default (ref: Q4, Q10). Rotation/compression is new infrastructure (Decision 4).
- **Structured CLI logging to a file, optionally stderr; configurable level (debug/info/warn/error); context always includes ticket ID, phase, trace ID.** Logs go to a file (and optionally stderr for interactive use) — never stdout, which is reserved for the single JSON envelope (ref: Q5, Q13). Log level is a new string-enum config setting with `coerce_log_level` defaulting to `info`, allowed `{debug,info,warn,error}` (Resolved Decisions OQ5).

## Delta

- **New file `scripts/qrspi_events.py`** — pure helpers (`build_event`, `event_trace_id`, `coerce_rotation_bytes`, `coerce_retention_days`, `coerce_log_level`, `events_path`, `rotate_if_needed`, `append_event`) plus a CLI printing one stdout envelope, importing `qrspi_paths`, mirroring `qrspi_metrics_append.py` shape. `events_path(repo_root)` returns `<main-root>/.qrspi/observability/events.jsonl` (single shared file, NOT per-ticket) (ref: Q3, Q5; Decision 2). `append_event` uses the `O_APPEND` single-`os.write` atomic-append mechanism (ref: Q8).
- **New file `scripts/qrspi_events_test.py`** — stdlib `unittest`, auto-discovered by `run_tests.py`; covers schema build, deterministic `trace_id` (`uuid5` stable per ticket), each `coerce_*` (including `bool` rejection), `events_path` resolution (single shared main-checkout path, no double-nesting), append round-trip + fail-closed, concurrent-append integrity (two writers, both lines present), and rotation across the size threshold via `tempfile` (ref: Q10, Q11).
- **Modified `scripts/qrspi_persist.py`** — emit the phase *success* event (and a *failure* event on its own `!ok` path) by calling the `qrspi_events` core directly, since persist already runs at the transition (no extra `agent()` round-trip) (ref: Q1, Q9; Decision 1).
- **Modified `scripts/qrspi_resolve.py`** — emit a *decision* event when it computes the next action (it already runs once per ticket) (ref: Q1; Decision 1).
- **Modified `.claude/workflows/qrspi-batch.js`** — for the JS-only points (per-artifact *start*, `agent()`→`null`, per-ticket thrown `catch`) emit a coarse event via one best-effort `agent()` call to `qrspi_events.py`; no inline event logic (logic-out-of-JS policy) (ref: Q1, Q12; Decision 1).
- **Modified `.qrspi/config.example.json`** — document the new flat keys: `eventLogRotationBytes` (10485760), `eventLogRetentionDays` (30), `logLevel` ("info") (ref: Q4, Q10).
- **Modified `.gitignore`** — add `.qrspi/observability/` (the event log is operational telemetry, rotated/pruned, and must not be committed) (ref: Q14; Decision 2 / OQ3).
- **Optional new contract-seam fixtures** under `scripts/fixtures/contract_seam/` only if a new JS `parse*` envelope parser is added for the event-writer worker (ref: Q12).

## Pattern Decisions

### Decision 1: Where event-emission logic lives (and how it reaches the file)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | A separate `agent()` round-trip to `qrspi_events.py` for **every** event | Uniform single emission path | A full agent spawn per log line — 6+ extra spawns per ticket/run on the hot path; cost + failure surface |
| B | Inline event writes in the JS shell | Fewest round-trips | Impossible — JS sandbox has no FS; violates logic-out-of-JS policy; untestable |
| C | **Fold emission into the Python scripts that already run at each transition; reserve a single best-effort JS→Python call only for the JS-only points** | No extra round-trip for the common success/decision/failure events; richest detail Python-side; minimal JS surface | Two emission paths (Python-direct + JS-coarse) to keep consistent |

**Recommendation:** Option C.
**Rationale:** The JS sandbox cannot do file IO and decision logic must live in tested Python by policy (ref: Q1, Q12). `qrspi_persist.py` already runs at the success gate and `qrspi_resolve.py` at the decision point, so those events cost no extra round-trip; a failing Python script can emit the richest failure event before its non-zero exit (ref: Q9). Only the per-artifact *start*, the `agent()`→`null` sentinel, and the thrown `catch` have no Python script in scope (ref: Q9) — those get one best-effort coarse JS→Python emission. `qrspi_metrics_append.py` is the near-exact template for the writer core (ref: Q3, Q5).
**NEW PATTERN?** No — generalizes the existing JSONL-append-with-verify writer and reuses existing script invocation points.

### Decision 2: Event-log file location (single-file requirement vs per-ticket isolation)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Per-ticket `<root>/.worktrees/<id>/.qrspi/<id>/events.jsonl` | Matches critic-metrics precedent; zero cross-worktree contention | Does NOT satisfy the literal "single file" AC; querying spans files (needs an aggregator); committed-log churn |
| B | **Single shared `<main-root>/.qrspi/observability/events.jsonl`, gitignored** | Satisfies the ticket AC literally; one queryable log with no aggregator; correct home for operational telemetry; shared by all worktrees via `resolve_repo_root` | Needs explicit append-atomicity for concurrent invocations; a definite gitignore entry |

**Recommendation:** Option B — a single shared file in the **main checkout** at `.qrspi/observability/events.jsonl`, gitignored.
**Rationale:** Observability events are cross-cutting **operational telemetry**, a different category from the per-ticket *evaluation/work* artifacts (`critic-metrics.jsonl`, `design.md`) that are committed into a ticket's branch. Placing the log in the main checkout (reachable from any worktree because `resolve_repo_root` yields the main root, ref: Q3) gives the single queryable log the ticket asks for, shared across all concurrent worktrees, without an aggregator. Append-atomicity under the rare concurrent-invocation case (in-run processing is sequential, ref: Q8) is provided cheaply by `O_APPEND` + a single `os.write()` per line with events bounded under PIPE_BUF.
**NEW PATTERN?** Yes — a single shared operational-telemetry log in the main checkout is a new (but well-bounded) layout; justified by the explicit single-file AC and by the telemetry-vs-artifact distinction.

### Decision 3: Correlation IDs (trace/span) without `Date.now()`/`Math.random()`

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | **All IDs Python-side: `trace_id = uuid5(NAMESPACE, ticket_id)` (deterministic), `span_id`/`event_id` = `uuid4()`, `parent_span_id` threaded from JS** | No anchor needed; avoids the JS prohibition entirely; reproducible; a ticket's whole lifecycle is one filterable trace | A re-run of the same ticket reuses its `trace_id` (runs separated by timestamp/span, not trace) |
| B | Per-phase, HEAD-anchored `uuid5(NAMESPACE, ticket_id + ':' + head_sha)` | Distinguishes re-runs | A "trace" fragments into one-per-phase; needs a `git rev-parse` per emission |
| C | Per-invocation run id minted in JS and threaded everywhere | "True" per-execution traces | Blocked — JS can't mint without `crypto.randomUUID` (flaky/absent in sandbox); the documented runId bug (ref: Q7) |

**Recommendation:** Option A — deterministic per-ticket `trace_id`, all IDs generated in the Python writer.
**Rationale:** The `Date.now()`/`Math.random()` prohibition is real and the historical runId is orphaned (ref: Q7); Python is the allowed source for both `timestamp` and IDs. `uuid5(NAMESPACE, ticket_id)` needs no run-anchor (dissolving the former OQ4), is stdlib and deterministic, and for the stated goals — debug a ticket's progression, measure phase duration, verify execution — a per-ticket trace plus per-event timestamps is sufficient; re-runs remain distinguishable by time window and `span_id`.
**NEW PATTERN?** Yes — trace/span correlation is greenfield; justified because no correlation primitive beyond `t.id` exists (ref: Q7).

### Decision 4: Rotation, compression, and retention

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Size-check before each append; on overflow rename to a timestamped sibling, gzip it, prune files older than retention | Self-contained in the writer; no external scheduler; testable via temp dir | Rotation runs in the append hot path (small cost); a rare rotate-race under concurrent invocations |
| B | Separate `qrspi_rotate.py` invoked on a schedule | Keeps append cheap | No scheduler exists in the harness; adds an unwired moving part |

**Recommendation:** Option A — rotation/retention inside `qrspi_events.py`, checked on append.
**Rationale:** The harness has no scheduler; the append path is the only guaranteed execution point, and the fail-closed verify pattern fits a pre-append size check (ref: Q3, Q11). Settings via `read_config` + `coerce_*` (ref: Q4, Q10). Residual: under two concurrent invocations both crossing the threshold, a rotate-race could leave a few lines in either the rotated or the fresh file; this is low-probability (sequential in-run processing, ref: Q8) and bounded (no data loss, only placement) — handled defensively in the plan (rotate via atomic `os.rename`, tolerate "already rotated"), not a design blocker.
**NEW PATTERN?** Yes — no rotation/compression precedent exists (ref: Q11); justified by the explicit ticket requirement with no reusable mechanism.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Ticket fields `error_code` / `backoff_duration` have no source, leading to fabricated values | high | med | Omit both; tie retry events to the actual `CI-Revise-Attempt` trailer; record only real values in optional `context` (OQ1) (ref: Q6) |
| Shared `events.jsonl` races under concurrent invocations | med | med | `O_APPEND` + single `os.write()` per line, events bounded under PIPE_BUF; in-run processing is sequential so true concurrency is rare (ref: Q8) |
| Rotation races under concurrent invocations (two writers rotate at once) | low | low | Atomic `os.rename` + tolerate "already rotated"; no data loss, only line placement (Decision 4) |
| The coarse JS→Python emission for failure points adds an `agent()` round-trip / failure surface | med | low | Best-effort: a failed event write logs but never blocks the phase, mirroring "a failed Linear write never blocks work"; folded Python-side emission (Decision 1C) keeps these to the few JS-only points (ref: Q1) |
| JS-emitted failure events lack detail (agent seam returns only `null`) | high | low | Emit rich failure events Python-side before non-zero exit; JS-side events record only that a phase failed (ref: Q9) |
| New JS event-writer envelope parser drifts from the Python producer | low | med | If a new `parse*` is added, add a fixture pair and extend both contract tests (ref: Q12) |

## Resolved Decisions

The five open questions raised during design were resolved in design review (2026-06-18):

- **OQ1 (backoff/error code) — DESCOPED.** No exponential-backoff policy or `error_code` exists in the review-gate pipeline (ref: Q6). Retry events are keyed to the real `CI-Revise-Attempt` trailer; `error_code` and `backoff_duration` are **omitted** (not fabricated). Adding a real backoff policy is deferred to a separate ticket. (Decision 1; Desired End State.)
- **OQ2 (single file vs per-ticket) — SINGLE SHARED FILE.** `<main-root>/.qrspi/observability/events.jsonl`, shared across worktrees, satisfying the literal AC. Justified by treating observability as operational telemetry rather than a per-ticket committed artifact. (Decision 2.)
- **OQ3 (committed vs gitignored) — GITIGNORED.** Add `.qrspi/observability/` to `.gitignore`; a rotated/compressed/retention-pruned log must not be tracked (pruning would delete tracked files; rotation churns the diff). (Decision 2; Delta.)
- **OQ4 (trace_id run-anchor) — DISSOLVED.** No run-anchor is needed: `trace_id = uuid5(NAMESPACE, ticket_id)` is deterministic and Python-generated. A ticket's lifecycle is one trace; re-runs are separated by timestamp and `span_id`. (Decision 3.)
- **OQ5 (log level default/set) — `info` + `{debug,info,warn,error}`.** `coerce_log_level` returns `info` for any unrecognized value, mirroring `coerce_cap`. (Desired End State; Delta.)
