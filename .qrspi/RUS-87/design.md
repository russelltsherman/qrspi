# Design — Monitoring and alerting on event-log signals for the qrspi review-gate pipeline

**Ticket:** RUS-87
**Research basis:** research.md @ 2026-06-18T22:00:00Z
**Generated:** 2026-06-18T23:00:00Z
**Status:** draft

> **Foundational caveat (read first).** Research establishes that the producer this ticket
> claims to consume — the RUS-85 event-log emitter writing `.qrspi/observability/events.jsonl` —
> **does not exist in this worktree** (ref: Q1, Inconsistencies). There is no event file, no
> schema, no `observability` directory, and no `.qrspi/RUS-85` artifact dir; the only "RUS-85"
> string in code is an unrelated restack regression (ref: Q1). The ticket is marked "Dependent on
> RUS-85", so the *correct* sequencing is for RUS-85 to land its emitter and schema first. This
> design therefore treats the **event schema as a contract that must be jointly owned with RUS-85**
> (see OQ1) and frames every consumer component against the *closest existing pattern* rather than a
> real producer. Where RUS-85 is genuinely absent, the work is greenfield and the design says so.

## Current State

- There is **no event-log emitter, no `.qrspi/observability/events.jsonl`, and no observability
  directory** anywhere in the repo (ref: Q1). The closest existing JSONL precedent is the per-ticket
  `critic-metrics.jsonl` ledger, whose lines are camelCase records (`ticketId`, `runId`,
  `terminalAction`) wrapped by a single "envelope authority" appender that injects
  `ticketId`/`timestamp`/`runId` (ref: Q1).
- There is **no tail, watch, polling, fs.watch, or rotation-following utility** in the codebase; all
  JSONL access is append-only writes and whole-file reads, with no reader-side offset, inode check,
  or rotation contract (ref: Q2, Q8).
- There is **no unified `qrspi` CLI binary and no `add_subparsers` router** (ref: Q3). Every command
  is a standalone `scripts/<name>.py` with its own `argparse` parser, a `main(argv=None)` entrypoint,
  `sys.exit(main())`, and self-location from `__file__` (ref: Q3, Discovered Patterns).
- There is **no handler-registry, pub-sub, or observer pattern** (ref: Q4). The only dispatch is a
  closed-enum, fail-closed JS `switch` on `decision.action` in the batch orchestrator; an unknown key
  is a hard error (ref: Q4).
- Config is read by `scripts/qrspi_config.py`, which resolves **exactly one top-level key**, is
  **string-valued only**, does **no nested/dot-path access and no type coercion**; the JS envelope
  parser rejects any non-string value (ref: Q5). Nested config already has a precedent: a
  purpose-built reader (`qrspi_critics_config.py`) per namespace, not an extension of the single-key
  reader (ref: Q5, Discovered Patterns).
- There is **no long-lived process, in-memory state store, or singleton** (ref: Q6). The architecture
  is one-shot processes; durable per-ticket state lives on disk in `.qrspi/<id>/` dirs, and the only
  cross-run counter lives as a git head-commit trailer with explicit resets (ref: Q6, Q8).
- There is **no per-line JSONL stream parser** and thus no "skip one bad line" precedent; malformed
  handling in the repo is bimodal — writers fail-closed, readers/reducers degrade to empty (ref: Q7).
- There is **no phase-timeout, grace-period, hang-detection, or `phase_start`/`phase_end` pairing**
  logic; `phase` exists only as a label on metrics records, never as a timed pair (ref: Q9). The only
  timeout is the 180s per-test-file subprocess kill in the test runner (ref: Q9).
- The test story is `scripts/<name>_test.py` siblings run by `scripts/run_tests.py`
  (subprocess-per-file, stdlib `unittest`, no pytest, CI-gated). Time and paths are **injected as
  arguments**, never clock-mocked; filesystem tests use `tempfile.TemporaryDirectory` (ref: Q10).
  Cross-component seams are tested with checked-in golden fixtures (wellformed + malformed) under
  `scripts/fixtures/contract_seam/`, not live e2e (ref: Q11).
- There is **no structured/JSON logging facility and no leveled (`warn`/`error`) logger** (ref: Q12).
  The convention is **stdout = one JSON envelope, stderr = prose diagnostics, exit code + `ok` = the
  success signal**; callers JS-parse stdout, so stdout must not be polluted (ref: Q12).

## Desired End State

Each acceptance criterion maps to concrete behavior below.

- **Tailer reads/parses JSONL in real time** → A new `scripts/qrspi_log_tail.py` reads the event file
  incrementally from a persisted byte offset, parses each complete `\n`-terminated line, and feeds
  parsed events to a reducer. "Real time" is implemented as **interval polling** (no fs.watch
  precedent exists, ref: Q2), default `observability.tailInterval=1000` ms.
- **Tailer handles rotation (detect, reopen, maintain position)** → On each poll the tailer compares
  the file's inode (and size-shrink) against the last seen identity; on rotation it reopens the new
  file and resets the offset to 0, preserving the offset otherwise (net-new mechanism, ref: Q8).
- **In-memory state per ticket (active phases, durations, retries)** → A pure reducer
  (`scripts/qrspi_log_state.py`) folds the event list into a per-`ticketId` state dict (started
  phases, start timestamps, status, retry history), resettable when a ticket completes. State is held
  as an explicit dict passed through the reducer, mirroring the **filesystem-keyed-by-ticket-id**
  durability precedent rather than a singleton (ref: Q6).
- **Phase duration histograms (min/max/avg/p50/p90/p95/p99 per phase type)** → A pure metrics
  function in `scripts/qrspi_log_metrics.py` computes percentiles over collected
  start→end durations per phase type.
- **Phase timeout alerts** → An evaluator compares each in-flight phase's elapsed time against its
  configured threshold (`observability.alerts.phaseTimeout`) and emits a `warn` alert.
- **Retry storm alerts** → The evaluator counts retries per ticket within
  `observability.alerts.retryStormWindow`; exceeding `retryStormCount` emits an `error` alert.
- **Error cascade alerts** → The evaluator groups identical `error_code` across tickets within
  `observability.alerts.errorCascadeWindow`; multi-ticket recurrence emits an `error` alert.
- **Silent phase alerts** → A phase with a start but no end after a grace period (a multiple of the
  tail interval, see OQ2) emits an alert; the grace window distinguishes "hung" from "not yet
  arrived" (net-new, ref: Q9).
- **Alert output to CLI log, correct level, JSON format** → Alerts are emitted as one JSON object per
  alert to **stderr** (preserving the stdout-is-envelope contract, ref: Q12), each carrying alert
  type, ticket_id, phase, threshold, actual_value, timestamp, and a `level` field. There is no
  existing leveled logger, so this defines a minimal convention (ref: Q12, see Decision 4).
- **`qrspi log query` command (summaries, timelines, error reports, perf stats)** → A new standalone
  `scripts/qrspi_log_query.py` (NOT a subcommand — no dispatcher exists, ref: Q3) reads the whole
  event file once and produces the four report types, JSON by default with a `--table` flag.
- **Query filtering (ticket_id, phase, event_type, date range, status)** → Flat `--ticket`,
  `--phase`, `--event-type`, `--since`, `--until`, `--status` flags on the query script, matching the
  flat-flag convention (ref: Q3).
- **Tailer disabled via `observability.tailEnabled=false`** → A new nested-config reader resolves the
  flag; when false the tailer exits immediately with `{ok:true, disabled:true}`.
- **Unit tests cover tailer, state store, metrics, alert evaluators** → Each new `scripts/qrspi_log_*.py`
  ships a `scripts/qrspi_log_*_test.py` sibling with a pure testable core and injected time/paths
  (ref: Q10).
- **Integration test: emitted events consumed, alerting fires** → Because no RUS-85 emitter exists
  (ref: Q11), the test uses **checked-in JSONL fixtures** (good + partial/malformed lines) under
  `scripts/fixtures/` consumed end-to-end through tail→reduce→alert, mirroring the contract-seam
  fixture pattern (ref: Q11). A synthetic emitter helper authored here stands in for RUS-85 until it
  lands (see OQ1).

## Delta

- **New files:**
  - `scripts/qrspi_log_tail.py` — incremental offset-based reader + rotation detection + poll loop;
    pure core (parse-lines-from-offset) separated from the IO/poll shell (ref: Q10).
  - `scripts/qrspi_log_state.py` — pure per-`ticketId` reducer (events → state dict).
  - `scripts/qrspi_log_metrics.py` — pure percentile/aggregate functions.
  - `scripts/qrspi_log_alerts.py` — pure alert evaluators (timeout, retry storm, error cascade,
    silent phase), each taking "now" and thresholds as arguments.
  - `scripts/qrspi_log_query.py` — standalone query CLI with flat filter flags and `--table`.
  - `scripts/qrspi_observability_config.py` — dedicated nested-config reader for `observability.*`
    with defaults + type coercion (the per-namespace-reader precedent, ref: Q5).
  - `scripts/qrspi_log_*_test.py` siblings for each of the above (ref: Q10).
  - `scripts/fixtures/observability/events_wellformed.jsonl`,
    `.../events_with_malformed_line.jsonl`, `.../events_rotation.jsonl` — golden inputs (ref: Q11).
- **Modified files:**
  - `.qrspi/config.example.json` — document the `observability.*` / `observability.alerts.*` keys and
    defaults.
- **No DB queries, middleware, or daemon registrations** — none of those constructs exist (ref: Q4,
  Q6). The "background watcher" is a poll-loop script, not a registered service.

## Pattern Decisions

### Decision 1: Tailing mechanism — interval polling vs fs.watch/inotify

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Interval polling: stat the file each tick, read from saved offset | Matches "no watch primitive exists" reality (ref: Q2); trivially testable by injecting offset+content; portable; rotation check is a stat compare | Latency bounded by interval; busy-poll cost (negligible at 1s) |
| B | fs.watch / inotify event-driven | Lower latency; no idle polling | Zero precedent in repo (ref: Q2); platform-flaky; harder to unit-test; over-engineered for a CLI harness |

**Recommendation:** Option A.
**Rationale:** The repo has no watch/poll primitive at all (ref: Q2), and the configurable
`tailInterval` default in the ticket presupposes polling. Polling keeps the pure core (read N lines
from offset) injectable and unit-testable per the DI convention (ref: Q10).
**NEW PATTERN?** Yes — there is no tailer in the repo. Justified: no existing reader follows file
growth or rotation (ref: Q2, Q8); a real-time consumer is net-new infrastructure regardless of
mechanism.

### Decision 2: Event field naming — camelCase vs snake_case

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | camelCase (`ticketId`, `eventType`, `errorCode`) | Matches the only JSONL precedent, `critic-metrics.jsonl` (ref: Q1); consistent with envelope-authority appender | Contradicts the snake_case the ticket/questions assume |
| B | snake_case (`ticket_id`, `event_type`, `error_code`) | Matches ticket wording | Clashes with the existing JSONL convention (ref: Inconsistencies); two JSONL dialects in one repo |

**Recommendation:** Option A (camelCase), **pending OQ1 alignment with RUS-85.**
**Rationale:** The codebase's sole JSONL convention is camelCase (ref: Q1, Discovered Patterns), and
the producer (RUS-85) is the schema owner. The consumer must match whatever RUS-85 actually emits —
so this is a *recommendation to converge on camelCase*, escalated as OQ1 because picking unilaterally
risks a producer/consumer schema split.
**NEW PATTERN?** No — reuses the existing camelCase JSONL convention (ref: Q1).

### Decision 3: Nested config access for `observability.*`

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | New dedicated reader `qrspi_observability_config.py` | Follows the documented per-namespace precedent (`qrspi_critics_config.py`, ref: Q5); can add type coercion + nested defaults | One more small reader file |
| B | Extend `qrspi_config.py` to do dot-paths | Single reader | Breaks its single-key string-only contract and the JS parser's non-string rejection (ref: Q5); exactly the RUS-56 trap (ref: Inconsistencies) |

**Recommendation:** Option A.
**Rationale:** `qrspi_config.py` is single-top-level-key, string-valued, no coercion (ref: Q5); nested
config already gets a purpose-built reader (ref: Q5, Discovered Patterns). RUS-56's lesson is explicit
that a nested consumer must bring its own mechanism (ref: Inconsistencies).
**NEW PATTERN?** No — mirrors the existing `qrspi_critics_config.py` per-namespace reader (ref: Q5).

### Decision 4: Malformed line and alert-output handling

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Tolerant reader: skip the unparseable line, continue; alerts → stderr JSON, stdout stays envelope | Matches reader-degrades-to-empty precedent (ref: Q7) and stdout-is-envelope contract (ref: Q12); a partial mid-flush line is expected in a live tail | Skipped lines need a stderr diagnostic so silent loss is visible |
| B | Fail-closed: abort the tail on any bad line | Matches writer fail-closed precedent (ref: Q7) | Wrong for a live stream — one mid-flush line would kill monitoring |

**Recommendation:** Option A.
**Rationale:** Readers/reducers in the repo degrade to empty rather than crash (ref: Q7), and a tailer
reading a file mid-append will routinely see partial lines (ref: Q7, Q8). Emitting alerts as JSON on
**stderr** preserves the "stdout = one machine envelope" contract that JS callers depend on (ref: Q12).
A skipped line gets a stderr prose note so loss is observable.
**NEW PATTERN?** Yes — per-line skip-and-continue has no precedent (ref: Q7); justified because the
bimodal repo rule (writers fail-closed, readers tolerant) does not cover a *stream*, and the tolerant
reader side is the closest fit.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| RUS-85 emitter is absent in this worktree, so there is no real producer or schema to consume (ref: Q1, Q11) | high | high | Treat the schema as a shared contract (OQ1); build against checked-in JSONL fixtures and a synthetic emitter; gate landing on RUS-85's schema, or sequence this ticket after RUS-85 lands |
| Field-naming split (camelCase vs snake_case) between producer and consumer (ref: Q1, Inconsistencies) | med | high | Lock the schema with RUS-85 before implementation (OQ1); centralize field names in one module so a flip is one edit |
| Long-lived poll loop is the first stateful, non-one-shot component; no precedent for lifecycle/shutdown (ref: Q6) | med | med | Keep all logic in a pure injectable core; the IO shell only loops + sleeps + reopens; bound it with `tailEnabled=false` and a clean exit envelope |
| Rotation/offset tracking is net-new; an inode reuse or truncate could re-read or drop events (ref: Q8) | med | med | Detect rotation via inode change AND size shrink; reset offset to 0 only on confirmed rotation; cover with the `events_rotation.jsonl` fixture |
| Silent-phase grace window mis-tuned → false hang alerts or missed hangs (ref: Q9) | med | med | Make the grace period a configurable multiple of the tail interval (OQ2); default conservative; unit-test the boundary with injected "now" |
| Nested config read regresses if someone routes it through `qrspi_config.py` (the RUS-56 trap) (ref: Q5) | low | med | Ship the dedicated reader (Decision 3) with tests asserting nested keys + coercion; document keys in `config.example.json` |

## Open Questions

- OQ1: What is RUS-85's *actual* emitted event schema — exact field names, casing (camelCase per repo
  precedent vs the snake_case the ticket assumes), the `phase_start`/`phase_end`/retry/error event
  taxonomy, and timestamp format? This must be co-owned with RUS-85 before implementation; the
  consumer cannot define it unilaterally without risking a producer/consumer split (ref: Q1,
  Inconsistencies).
- OQ2: What silent-phase grace period is acceptable per phase type (and is it a fixed config value or
  a multiple of `tailInterval`)? The ticket gives phase-timeout defaults but no silent-phase grace
  default (ref: Q9).
- OQ3: Is RUS-87 expected to land *before* RUS-85's emitter exists (building against fixtures only), or
  should it be sequenced strictly after RUS-85 so the integration test runs against the real producer
  (ref: Q11)? This changes whether the synthetic emitter is throwaway or a permanent test double.
- OQ4: Should the long-lived tailer be a foreground poll-loop script the operator runs manually, or is
  it expected to be wired into the batch orchestrator's lifecycle? The repo has no daemon/service
  precedent to infer this from (ref: Q6).
