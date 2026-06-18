# Design — Monitoring and alerting on event-log signals for the qrspi review-gate pipeline

**Ticket:** RUS-87
**Research basis:** research.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Current State

There is **no event-log producer in this worktree**: no module writes `.qrspi/observability/events.jsonl`, no such file or directory exists, and there is no `emit_event`/`event_type` writer anywhere (ref: Q1). The ticket's parent RUS-85 — the dependency that "produces what this layer consumes" — is therefore unmerged/absent here (the worktree's git metadata was also detached, so branch state could not be confirmed) (ref: Inconsistencies). The only JSONL artifact actually produced is the **critic-metrics ledger** `.qrspi/<id>/critic-metrics.jsonl`, written by `scripts/qrspi_metrics_append.py` (ref: Q1). That ledger is the sole structural precedent for everything this ticket builds.

The existing JSONL writer is **append-only, per-ticket, and never rotated**: `append_line` opens the file in `"a"` mode, writes one `json.dumps(line) + "\n"`, and uses `os.path.getsize` only to fail-closed on empty — no rename, size-cap, or roll exists, and no rotated-file naming convention exists to detect (ref: Q2). Provenance fields are injected by the appender (`ticketId`, `timestamp` as UTC ISO-8601, `runId`) and always win over the record; existing lines are **camelCase** (ref: Q1). No code reads any JSONL file back, so there is **no existing reader, no partial-line tolerance, and no rotation/reopen handling** — all net-new (ref: Q7, Q8).

There is **no top-level `qrspi` CLI binary or subcommand dispatcher** and no `add_subparsers` anywhere; every capability is a standalone `python3 scripts/qrspi_<verb>.py` with its own `argparse`, `required=True` flags, self-located repo root, a single `{ok, ...}` JSON envelope on stdout, and a pure core behind a thin `main(argv=None)` (ref: Q3). Config has **two readers**: the generic `qrspi_config.py` reads one flat top-level string key only (the JS `parseConfigEnvelope` rejects non-string values), while nested blocks like `critics.*` are read **only** by a dedicated, tested resolver (`qrspi_critics_config.py`) that reads `config.json` once and walks the nested structure with config>default precedence (ref: Q4). Per-ticket state is **not held in a long-lived store** — it is derived on demand by the pure `qrspi_resolve_state.resolve` and iterated transiently by `qrspi-batch.js`; there is no `Dict[ticket_id, State]` to extend (ref: Q5). "Completion" is a derived resolver condition (`action="land"`) plus the Linear `Done` status, **not a discrete event** (ref: Q6).

There is **no leveled logging facility** (no `import logging` in `scripts/`); Python tools emit one JSON envelope to stdout (`ok` + optional `error`/`warnings`), with severity binary, while human progress is the JS `log()` injected global, off-limits to Python tools (ref: Q11). There is **no percentile, histogram, or alert-formatting utility** — the only `p95` hit is a test fixture token, not an implementation (ref: Q12). The unit-test convention is firmly established: a stdlib-only `unittest` sibling `scripts/qrspi_<x>_test.py` per module, importing the pure core, using `tempfile.TemporaryDirectory()`, discovered and run as subprocesses by `scripts/run_tests.py` and gated in CI (ref: Q9). The `evals/` harness and `run_eval.py` are non-functional placeholders; integration coverage = pure core + tempdir/fixture JSONL inputs asserted via `unittest` (ref: Q10).

## Desired End State

Because RUS-85 is absent (see Risk 1 / OQ1), this design is built against an **explicit, documented event-line contract** (the Event Schema Contract decision below) that a tailer parses defensively; if RUS-85 ships a different schema, only the parser/adapter changes. Each acceptance criterion maps as follows:

- **Tailer reads/parses events in real-time** → a `qrspi_event_tailer.py` pure core that, given a file path + a byte offset, reads newly-appended complete `<json>\n` lines, parses each, and returns parsed events + the new offset; a thin polling driver re-invokes it every `tailInterval` ms (ref: Q3, Q7).
- **Tailer handles rotation, maintains read position** → the tailer tracks `(inode/device, offset)`; on a detected inode change or shrink it reopens at offset 0, preserving prior position semantics. Since no rotation precedent exists this is net-new (ref: Q2).
- **In-memory state per ticket (active phases, durations, retries)** → a pure `qrspi_event_state.py` reducer: `reduce(state, event) -> state`, keyed by `ticket_id`, recording phase-start times, computing durations on phase-end, accumulating retry history, and resetting a ticket's entry on a completion signal (ref: Q5, Q6).
- **Phase duration histograms (min/max/avg/p50/p90/p95/p99)** → a pure `qrspi_event_metrics.py` using `statistics.quantiles` (stdlib 3.8+), per phase type (ref: Q12).
- **Phase timeout / retry storm / error cascade / silent phase alerts** → pure evaluator functions in `qrspi_event_alerts.py`, each taking current state + thresholds + a "now" clock and returning zero or more alert payloads. Silent-phase and error-cascade need cross-event/cross-ticket accumulation that only the state store can provide (ref: Q5, Q8).
- **Alert output at correct level, JSON format** → each alert payload is a JSON object with `level` (`warn`/`error`), `type`, `ticket_id`, `phase`, `threshold`, `actual_value`, `timestamp`. The Python core returns payloads; the JS driver forwards them to `log()` (level is net-new but fits the stdout-JSON discipline) (ref: Q11).
- **`qrspi log query` produces summaries/timelines/error/perf reports** → a standalone `scripts/qrspi_log_query.py` (not a subcommand) that reads the whole event log and emits a `{ok, ...}` envelope; `--table` for human output (ref: Q3).
- **Query filtering by ticket_id/phase/event_type/date range/status** → flags on `qrspi_log_query.py`, filtering applied in its pure core (ref: Q3).
- **Tailer disabled via `observability.tailEnabled=false`** → read through a new nested resolver `qrspi_observability_config.py` (ref: Q4).
- **Unit tests cover tailer/state/metrics/alert evaluators** → one `*_test.py` sibling per new module (ref: Q9).
- **Integration test: RUS-85 events consumed, alerting fires** → a fixture-driven test writing synthetic JSONL to a tempdir and driving the full tailer→reducer→evaluator chain, asserting alert payloads (ref: Q10). True end-to-end through real RUS-85 code is **blocked** until RUS-85 merges (Risk 1).

## Delta

New standalone scripts (each with a pure core + `main(argv=None)` + a `*_test.py` sibling, stdlib-only, self-locating repo root via `qrspi_paths.resolve_repo_root`):

- `scripts/qrspi_event_tailer.py` — offset/inode-tracking line reader with rotation detection and partial-line tolerance.
- `scripts/qrspi_event_state.py` — pure per-`ticket_id` reducer (phase state, durations, retry history, reset-on-complete).
- `scripts/qrspi_event_metrics.py` — percentile/histogram + retry-frequency + success/failure-rate + e2e-duration calculators.
- `scripts/qrspi_event_alerts.py` — four pure evaluators (phase timeout, retry storm, error cascade, silent phase) returning leveled JSON alert payloads.
- `scripts/qrspi_observability_config.py` — dedicated nested resolver for `observability.*` (mirrors `qrspi_critics_config.py`), returning a complete defaults-filled envelope.
- `scripts/qrspi_log_query.py` — the query CLI (pure filter/report core + thin CLI).

New test fixtures under `scripts/fixtures/` — synthetic `events.jsonl` samples (clean, rotated, partial-trailing-line, timeout/storm/cascade/silent scenarios).

Modified: `.qrspi/config.example.json` — document the `observability.*` keys and defaults. Optionally `.claude/workflows/qrspi-batch.js` — a tail driver loop that polls the tailer and forwards alerts to `log()` (the only non-unit-testable seam; gate via JS↔Python contract fixtures per project convention). No existing Python module is modified (additive).

## Pattern Decisions

### Decision 1: Event-line schema contract (the load-bearing gap)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Adopt the **questions' speculative** snake_case schema (`event_type`, `error_code`, `ticket_id`) verbatim | Matches ticket text directly | Unverified — exists in no code; clashes with codebase camelCase ledger convention (ref: Q1, Inconsistencies) |
| B | Define an **explicit documented contract** in this design + a single parser/adapter; tailer is schema-tolerant (skips unparseable lines) | Decouples consumer from absent producer; one place to change when RUS-85 lands; defensive parsing already required for partial lines | Risk of drift from real RUS-85 schema until co-verified |
| C | Block the ticket entirely until RUS-85 merges | Zero rework risk | Stalls all autonomously-buildable work (tailer/metrics/alerts/query cores are producer-agnostic) |

**Recommendation:** Option B.
**Rationale:** The tailer must already tolerate partial/garbage lines (ref: Q7), so a single tolerant parser/adapter is a natural seam. The pure cores (reducer, metrics, alerts, query) operate on a normalized internal event record, so the only RUS-85-coupled surface is the adapter — minimizing rework when the real schema arrives. This also lets the bulk of the work proceed under the dependency gap rather than stalling (Option C). The contract MUST be confirmed against RUS-85 before merge (OQ1).
**NEW PATTERN?** Yes — there is no existing event-line contract; the closest precedent is the critic-metrics envelope, whose camelCase provenance fields (`ticketId`/`timestamp`/`runId`) the contract should align with rather than the questions' snake_case (ref: Q1).

### Decision 2: Nested `observability.*` config reading

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Use the generic flat `qrspi_config.py` | Reuses existing reader | **Impossible** — flat single-key, string-only; JS rejects non-string/nested values (ref: Q4) |
| B | New dedicated `qrspi_observability_config.py` mirroring `qrspi_critics_config.py` (single read, walk nested block, complete defaults-filled envelope) | Proven precedent; defaults centralized; never special-cases missing branches | Another config resolver to maintain |

**Recommendation:** Option B.
**Rationale:** Q4 is explicit that nested keys CANNOT use the flat reader and must follow the `qrspi_critics_config.py` precedent — and project memory records this exact mismatch biting RUS-56. Single-read discipline + complete defaults-filled envelope is the established contract (ref: Q4).
**NEW PATTERN?** No — directly mirrors the existing nested-resolver pattern.

### Decision 3: Query interface shape (`qrspi log query`)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add a `log query` subcommand to a new umbrella `qrspi` dispatcher | Matches ticket's literal `qrspi log query` phrasing | No dispatcher exists anywhere; would invent an umbrella CLI against the codebase grain (ref: Q3) |
| B | Standalone `scripts/qrspi_log_query.py` with flags, `{ok,...}` stdout envelope, `--table` | Matches the universal standalone-script-per-tool idiom; testable pure core | Invocation is `python3 scripts/qrspi_log_query.py ...`, not literally `qrspi log query` |

**Recommendation:** Option B.
**Rationale:** Q3 is unambiguous — there is no subcommand dispatcher; every tool is a standalone script. Building an umbrella CLI to honor literal phrasing would be a large, off-grain new pattern. The literal `qrspi log query` invocation is an OQ (OQ2).
**NEW PATTERN?** No — standard standalone-script idiom.

### Decision 4: Tail driver location (the orchestration seam)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Polling loop + alert dispatch lives in `qrspi-batch.js`, calling the Python tailer/reducer/evaluator cores | Aligns with functional-core/imperative-shell split; `log()` is JS-only (ref: Q11) | `qrspi-batch.js` is not unit-testable; needs contract-fixture coverage |
| B | A long-running Python daemon owning the loop | Self-contained, testable loop | No daemon precedent; duplicates the imperative-shell role; can't call the JS `log()` global |

**Recommendation:** Option A.
**Rationale:** All real logic stays in tested pure Python cores; only the thin poll-and-forward loop lives in JS, matching the codebase's split and the fact that leveled human output goes through the JS `log()` global (ref: Q11, Discovered Patterns). Cover the JS↔Python seam with contract fixtures per project convention.
**NEW PATTERN?** No — extends the existing imperative-shell pattern.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| RUS-85 producer is absent from this worktree — the entire data source this layer consumes does not exist (ref: Scope Note, Q1) | high | high | Build all producer-agnostic cores against a documented contract (Decision 1); isolate RUS-85 coupling to one adapter; confirm/align schema before merge (OQ1); treat true e2e as blocked until RUS-85 lands |
| Event schema casing/field mismatch (questions snake_case `event_type`/`error_code` vs codebase camelCase `ticketId`/`runId`) (ref: Inconsistencies, Q1) | high | med | Pin field names in the Decision 1 contract aligned to codebase camelCase; centralize in the adapter so a rename is one edit |
| Tailer reads a partial/in-flight trailing line or garbage; no existing reader tolerates this (ref: Q7) | med | med | Pure core only emits complete `<json>\n` lines, holds back a trailing newline-less fragment, and skips unparseable lines rather than crashing; fixture test for truncated final line |
| Rotation detection is net-new with no precedent; a missed rotation drops events or double-reads (ref: Q2) | med | med | Track `(inode, device, size)`; reopen at offset 0 on inode change or shrink; fixture test simulating a rotate-and-reopen |
| Silent-phase / crash detection has no precedent and depends on a wall-clock grace period (ref: Q8) | med | med | Make grace period configurable; evaluate against an injected `now` clock (pure, testable); document that a missing phase-end is inferred, never certain |
| Nested config wrongly routed through the flat reader (the RUS-56 failure mode) (ref: Q4) | low | high | Mandate the dedicated `qrspi_observability_config.py` resolver (Decision 2); unit-test defaults-filled envelope |
| No functional e2e harness; integration AC can only be met via fixtures (ref: Q10) | high | low | Fixture-driven integration test through the full chain in a tempdir; flag real-e2e as manual/blocked (OQ1) |

## Open Questions

- OQ1: RUS-85 is not present in this worktree. What is the **actual** committed event-line schema (exact field names, casing, `event_type`/`phase`/`error_code`/completion-signal values) and the **actual** file path/rotation behavior? The Decision 1 contract must be reconciled with the real producer before this layer can be verified end-to-end. Should this ticket proceed against the documented contract now, or block on RUS-85 merging first?
- OQ2: The ticket specifies a literal `qrspi log query` invocation, but no umbrella `qrspi` CLI exists (ref: Q3). Is a standalone `python3 scripts/qrspi_log_query.py` acceptable, or is standing up an umbrella dispatcher in scope (a much larger change touching every existing tool)?
- OQ3: For the tailer's start policy on a pre-existing non-empty log (tail-from-start vs tail-from-end), and for "completion" reset (infer from a `land` action event, a `Done` status, or a producer-emitted completion event — none confirmed to exist, ref: Q6) — which signal should the state store key its per-ticket reset on?
- OQ4: Should event field names follow codebase camelCase (`ticketId`) or the ticket's snake_case (`ticket_id`) in both stored events and alert payloads? This must match whatever RUS-85 emits (ref: Inconsistencies).
