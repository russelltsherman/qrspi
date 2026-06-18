# Design — Monitoring and alerting on event-log signals for the qrspi review-gate pipeline

**Ticket:** RUS-87
**Research basis:** research.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

> **Framing note (read first):** Research established that the upstream RUS-85
> event-log subsystem this ticket consumes **does not exist in this worktree** — no
> `.qrspi/observability/`, no `events.jsonl`, no emitter, no `phase_start`/`phase_end`/
> `event_type`/`error_code` symbols anywhere (ref: top-level finding; Q1; Q2; Q3; Q7;
> Q12). Nine of thirteen questions target absent code. This design therefore (1)
> defines the **producer-side contract** RUS-87 depends on as an explicit Open
> Question / Risk, and (2) shapes every consumer component to the repo's **real**
> conventions — stateless per-invocation re-derivation, one-script-one-purpose
> stdlib-only Python CLIs, JSON-envelope-over-exit-code — rather than the
> long-running-daemon / leveled-logger / dotted-config / subcommand-dispatcher premises
> the ticket assumes, none of which exist (ref: Q4; Q5; Q6; Q13).

## Current State

- There is **no event-log emission subsystem**: `.qrspi/observability/events.jsonl` and
  any `phase_start`/`phase_end`/`event_type`/`error_code` emitter are absent from the tree
  (ref: top-level finding; Q1; Q3). The only structured JSONL ledger that exists is the
  RUS-77 critic-metrics family, written one camelCase JSON object per line by
  `scripts/qrspi_metrics_append.py` with envelope keys `ticketId` / `timestamp` / `runId`
  (ref: Q1).
- That ledger is **append-only with no rotation** — `append_line` opens `"a"` and writes
  unconditionally, never renaming/truncating/size-capping, so there is no precedent rotation
  scheme or inode/size-shrink signal to reuse (ref: Q2). The append is plain buffered I/O
  with **no fsync, atomic rename, or lock**, so partial lines are possible (ref: Q8).
- There is **no unified `qrspi` CLI binary, no `add_subparsers` dispatcher, and no
  `--table`/`--json` output-mode convention**; the harness is a flat set of independent
  `python3 scripts/<name>.py` scripts, each with its own `argparse`, printing one JSON
  envelope to stdout and signalling via exit code (ref: Q4).
- **Both config readers are single-top-level-key only.** `scripts/qrspi_config.py` does
  `dict.get` with no dot-splitting, and JS `parseConfigEnvelope` rejects any non-string value;
  nested config is handled either by a dedicated per-concern resolver (`qrspi_critics_config.py`)
  or by flattening the key (`ciReviseCap`) (ref: Q5).
- There is **no long-running watcher/daemon and no in-memory cross-invocation state**: every
  entry point is short-lived and single-pass; `qrspi-batch.js` runs one pass and exits, and
  durable state lives on disk (ledgers) or in git (the `CI-Revise-Attempt` trailer) and is
  re-derived each run (ref: Q6).
- The resolver `scripts/qrspi_resolve_state.py` has **zero temporal logic** — no notion of
  duration, staleness, timeout, or hang; it reasons over discrete PR signals plus a *count*
  cap (`ciReviseCap`), so there is nothing time-based to reconcile a "silent phase" grace
  period against (ref: Q10). All timestamps in the repo are UTC ISO-8601 wall-clock via
  `datetime.now(timezone.utc).isoformat()`, parsed with `datetime.fromisoformat` (ref: Q10).
- There is **no `logging` facility and no warn/error level abstraction** anywhere in the
  Python scripts; "logging" is the `{ok, error?}` JSON envelope + exit code (machine) and an
  unleveled JS `log()` (human) (ref: Q13).
- The **tolerant JSONL read pattern** exists and is reusable: `qrspi_critic_summary._read_lines`
  reads line-by-line, skips blanks, `json.loads` each, and on `JSONDecodeError` or non-dict
  **skips + increments an aborted counter** rather than raising (ref: Q8). Tests are stdlib
  `unittest`, one `<name>_test.py` sibling per script, aggregated by `scripts/run_tests.py`
  (subprocess per file, CI gate); synthetic-line fixtures use `tempfile` inline (ref: Q11).
  There is **no real integration tier** — `evals/`/`run_eval.py` is a documented placeholder
  and e2e is manual (ref: Q12).

## Desired End State

Each acceptance criterion maps to a concrete component. Because there is no resident process
(ref: Q6), the design replaces the ticket's "real-time tailer + live in-memory store" with
**single-pass, re-derive-from-disk** components that process the event log up to its current
end on each invocation — the only model the repo supports. "Real-time" is satisfied by an
optional thin polling loop wrapper, kept out of the tested core.

- **Tailer reads + parses events from JSONL (AC1):** a `scripts/qrspi_event_read.py` reader
  consumes the log from a caller-supplied byte offset to EOF, parsing each line with the
  tolerant skip+count loop (ref: Q8), returning parsed events plus the new offset.
- **Rotation handling (AC2):** the reader detects rotation by comparing recorded file
  identity (size-shrink and, where available, inode) against the stored cursor; on rotation it
  resets the offset to 0 and reopens (ref: Q2 — net-new, no precedent). The cursor (offset +
  identity) is the durable read position, persisted to disk between passes per the
  stateless-re-derivation invariant (ref: Q6).
- **Per-ticket state — active phases, durations, retries (AC3):** a pure
  `qrspi_event_state.build_state(events)` folds the full event sequence into a per-ticket
  dict keyed by ticket id, pairing `phase_start`/`phase_end` for durations and counting retries;
  it is **recomputed from the log each pass**, not held resident (ref: Q3; Q6). A ticket
  "completed" terminal event resets its entry (ref: Q7 — terminal signal is an Open Question).
- **Duration histograms min/max/avg/p50/p90/p95/p99 per phase type (AC4):** a pure
  `qrspi_event_metrics.compute(state)` over the folded durations, stdlib-only percentile math.
- **Phase-timeout / retry-storm / error-cascade / silent-phase alerts (AC5–8):** pure alert
  evaluators in `qrspi_event_alerts.py`, each a function `(state|events, thresholds, now) →
  [alerts]`. Timeout, silent-phase, and storm/cascade windows compare event timestamps to a
  caller-injected `now` (UTC ISO-8601, ref: Q10) — no wall-clock read inside the tested core.
- **Alert output: CLI log, correct level, JSON (AC9):** since no logger exists (ref: Q13),
  alerts are emitted as **machine-parseable JSON lines on stdout**, each carrying
  `{alertType, level, ticketId, phase, threshold, actualValue, timestamp}`; `level` is a
  string field (`warn`/`error`) — net-new convention, not a log-sink integration.
- **`qrspi log query` command (AC10) + filters (AC11):** delivered as a standalone
  `scripts/qrspi_log_query.py` (there is no dispatcher to plug into, ref: Q4) with its own
  `argparse` exposing `--ticket-id`, `--phase`, `--event-type`, `--since`/`--until`, `--status`
  filters, producing ticket summaries, phase timelines, error reports, and performance stats.
  JSON envelope is the default output; `--table` adds a human-readable rendering (net-new flag).
- **Disable via `observability.tailEnabled=false` (AC12):** read by a dedicated observability
  config resolver (ref: Q5 precedent), the polling-loop wrapper is a no-op when disabled.
- **Unit tests for tailer/state/metrics/alerts (AC13):** one `<name>_test.py` sibling per new
  script, stdlib `unittest`, registered automatically by `run_tests.py` (ref: Q11).
- **Integration test: real RUS-85 emission → consumed → alerts fire (AC14):** there is no
  emission harness and no integration tier (ref: Q12). This AC is **blocked on RUS-85** and is
  the central Open Question / Risk below; the design substitutes a contract-fixture test (the
  repo's real seam-coverage pattern, ref: Q12) plus a documented manual e2e once RUS-85 lands.

## Delta

**New files (each stdlib-only, self-locating, JSON-envelope, with a `_test.py` sibling):**

- `scripts/qrspi_event_read.py` — offset-cursored tolerant JSONL reader + rotation detection.
- `scripts/qrspi_event_state.py` — pure fold of events → per-ticket state (phases, durations, retries).
- `scripts/qrspi_event_metrics.py` — pure percentile/aggregate calculator over folded state.
- `scripts/qrspi_event_alerts.py` — pure alert evaluators (timeout, retry-storm, error-cascade, silent-phase).
- `scripts/qrspi_obs_config.py` — dedicated observability config resolver (dotted keys → standard envelope).
- `scripts/qrspi_log_query.py` — `qrspi log query` CLI (filters, summaries, timelines, reports; `--table`).
- `scripts/qrspi_event_watch.py` — thin optional polling wrapper composing read→state→alerts→emit (untested shell).
- Matching `*_test.py` siblings for all of the above except the watch wrapper (harness-coupled, like qrspi-batch.js).

**Modified files:**

- `.qrspi/config.example.json` — add `observability.*` keys (tailInterval, tailEnabled, alerts.*),
  documented as read by `qrspi_obs_config.py` (mirrors the `critics.*` precedent, ref: Q5).
- `.qrspi/templates/` — no change (reference only).
- `scripts/run_tests.py` — no change needed; it auto-discovers new `*_test.py` (ref: Q11).

**New consumed contract (does not exist yet — see Open Questions):** the RUS-85 per-line event
schema. The design assumes the repo's camelCase ledger envelope (`ticketId`, `timestamp`,
`runId`) plus event fields (`eventType`, `phase`, `errorCode`); the snake_case the ticket uses
(`ticket_id`, `event_type`) **contradicts the established convention** (ref: Q1) and must be
pinned with RUS-85.

## Pattern Decisions

### Decision 1: Process model — resident watcher vs single-pass re-derivation

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Introduce a long-running daemon holding live in-memory state | Matches ticket's literal "real-time, in-memory store" wording; sub-second latency | First resident process in the repo; breaks the stateless-re-derivation invariant (ref: Q6); untestable in the stdlib-unittest model; lifecycle/crash-recovery all net-new |
| B | Single-pass re-derivation: pure fold of the log on each invocation; an optional thin polling wrapper re-invokes the pure core; durable cursor on disk | Matches the repo's only state model (ref: Q6); pure functions are directly unit-testable (ref: Q11); cursor persistence mirrors the git-trailer/ledger precedent | "Real-time" becomes "poll-interval-real-time"; state recomputed each pass (cost grows with log size until rotation) |

**Recommendation:** Option B.
**Rationale:** The repo has *only* short-lived single-pass invocations and re-derives all state
from disk/git each run (ref: Q6); the CI-revise counter is a commit trailer, not memory. A
resident daemon would be the first of its kind and is incompatible with the stdlib-unittest gate
(ref: Q11). The pure-core + thin-wrapper split keeps every alert/metric/state rule testable.
**NEW PATTERN?** Partial — the *pure fold + disk cursor* reuses existing precedents, but the
**polling-loop wrapper is net-new** (no `while`/poll/tail control flow exists today, ref: Q6).
Justified: a producer-driven stream genuinely needs a poll seam the current codebase lacks; it
is isolated in an untested shell so it does not weaken the tested core.

### Decision 2: Observability config reads (dotted `observability.*` keys)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Extend `qrspi_config.py` with generic dot-path support | One reader for everything | Changes a shared single-key reader relied on across the harness; JS `parseConfigEnvelope` still rejects non-string values (ref: Q5), so nested objects break the JS seam anyway |
| B | Dedicated `qrspi_obs_config.py` resolver emitting the standard envelope (per-concern, like `qrspi_critics_config.py`) | Matches the established nested-config precedent exactly (ref: Q5); isolates the parsing; no blast radius on the shared reader | One more small script |
| C | Flatten every key (`observabilityTailInterval`, …) like `ciReviseCap` | Fits the single-key reader verbatim (ref: Q5) | Loses the ticket's `observability.alerts.phaseTimeout` nested object (a per-phase map); flattening a map is awkward |

**Recommendation:** Option B.
**Rationale:** Research names the dedicated-resolver-per-concern approach as *the* established
pattern for nested config, citing `qrspi_critics_config.py` for `critics.design.maxRounds` and
explicitly warning against assuming a generic dotted reader (ref: Q5). The phase-timeout default
is a per-phase map (`{design, plan, implement}`), which flattening (Option C) handles poorly.
**NEW PATTERN?** No — it directly replicates the `qrspi_critics_config.py` precedent.

### Decision 3: Alert output channel

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Adopt stdlib `logging` with warn/error levels and a sink | Conventional severity model the ticket implies | No `logging` usage exists anywhere (ref: Q13); introduces a logging facility, sink config, and level filtering as net-new infra; inconsistent with the rest of the harness |
| B | Emit alerts as machine-parseable JSON lines on stdout, `level` as a string field | Matches the repo's JSON-envelope-over-exit-code convention (ref: Q13); machine-parseable per AC9; trivially testable | "level" is data, not a real log severity; no filtering/sink (acceptable — AC asks for JSON + level field, not sink integration) |

**Recommendation:** Option B.
**Rationale:** There is no leveled log sink to conform to (ref: Q13); AC9 requires JSON output
carrying a level, which a `{...,"level":"warn"}` line satisfies without inventing a logging
subsystem. Consistent with every other script's stdout-JSON channel.
**NEW PATTERN?** No (reuses the JSON-envelope channel) — though the **`level` field taxonomy**
(`warn`/`error`) is a small net-new convention, flagged explicitly.

### Decision 4: Time injection for timeout / window evaluators

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Evaluators read `datetime.now(timezone.utc)` internally | Fewer args | Non-deterministic; hard to unit-test silent-phase/storm windows (ref: Q11) |
| B | Caller injects `now` (UTC ISO-8601); evaluators are pure functions of (events, thresholds, now) | Deterministic, directly testable with fixtures (ref: Q11); the wrapper supplies real `now` | One extra parameter |

**Recommendation:** Option B.
**Rationale:** Research shows the repo splits pure logic into argument-driven helpers so tests
drive them with in-memory data (ref: Q11), and all timestamps are UTC ISO-8601 (ref: Q10).
Injecting `now` keeps the windowed alerts deterministic under the stdlib-unittest gate.
**NEW PATTERN?** No — it is the existing argument-driven-helper testing convention applied to time.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| RUS-85 producer absent — no event log, emitter, or schema to consume (ref: top-level finding; Q1; Q3; Q12) | high | high | Treat RUS-85 as a hard upstream dependency (it is the ticket's stated blocker). Pin the per-line schema as a written contract before coding; build the consumer against that contract with fixture-driven tests; defer the real-emission integration test (AC14) until RUS-85 lands. Do not start without the schema (Open Question). |
| Field-naming mismatch: ticket says snake_case (`ticket_id`, `event_type`); repo convention is camelCase (`ticketId`, `timestamp`) (ref: Q1; inconsistencies) | high | med | Resolve the casing in the RUS-85 contract; have the reader normalize once at the parse boundary so downstream pure functions see a single canonical shape regardless of which casing RUS-85 chooses. |
| Rotation detection is net-new with no precedent signal (no inode/size-shrink contract exists) (ref: Q2) | med | med | Define rotation detection against the RUS-85 rotation scheme (Open Question); use size-shrink as the primary portable signal plus inode where the OS exposes it; cover with a fixture that truncates/replaces a temp file. |
| Partial/truncated lines from non-atomic producer writes (ref: Q8) | med | low | Reuse the tested tolerant reader pattern (skip + count aborted) from `qrspi_critic_summary._read_lines`; never raise on a bad line; surface an aborted-line count in the reader envelope. |
| Recompute-each-pass cost grows with unbounded log until rotation (ref: Q2; Q6) | med | med | Persist the read cursor (offset) so each pass only folds new bytes; bound resident-state memory by resetting per-ticket entries on the terminal/completed event (ref: Q7). |
| "Silent phase" grace period is the first time-based bound in a purely event/count-driven decision layer (ref: Q10) | med | med | Keep the temporal logic entirely inside the new observability components (do not touch the resolver, which has no temporal state); inject `now` for determinism; default grace from `observability.alerts.*` config. |
| Integration tier does not exist; `evals/`/`run_eval.py` is a placeholder (ref: Q12) | high | low | Cover the JS↔Python/producer↔consumer seam with contract fixtures (the repo's real pattern); document a manual e2e procedure for AC14 rather than claiming an automated integration suite. |

## Open Questions

- OQ1: **What is the exact RUS-85 per-line event schema?** Required keys, event-type
  vocabulary (`phase_start`/`phase_end`/error/terminal), the start/end pairing key, and the
  field casing (snake_case per ticket vs camelCase per repo, ref: Q1; Q3). The consumer cannot
  be correctly built until this contract is pinned. Has RUS-85 actually landed elsewhere, or is
  this worktree simply missing it?
- OQ2: **What terminal event marks a ticket "completed"** for state reset (ref: Q7)? Today
  "completed" is a derived PR/Linear-`Done` state with no emitted record; RUS-85 must emit a
  terminal event, or the state store needs an alternative reset trigger.
- OQ3: **What is RUS-85's rotation scheme** (rename vs truncate, size/time trigger) and what
  file-identity signal does it leave for the tailer (ref: Q2)? Rotation detection is net-new and
  must match the producer's actual behavior.
- OQ4: **Is the optional polling-loop wrapper in scope, or is single-pass-on-demand enough?**
  The repo has no resident process (ref: Q6); confirm whether "real-time" truly requires a
  persistent poll loop or whether invoking the consumer per batch pass satisfies the intent.
- OQ5: **Should `observability.alerts.phaseTimeout` stay a nested per-phase map** (favoring the
  dedicated resolver, Decision 2B) or be flattened per-phase to fit the single-key reader
  (Decision 2C)? Confirms the config shape before `qrspi_obs_config.py` is written.
