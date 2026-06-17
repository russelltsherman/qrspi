# Design — Structured phase-gate event log: systematic logging for the qrspi review-gate pipeline

**Ticket:** RUS-86
**Research basis:** research.md @ 2026-06-17T00:00:00Z
**Generated:** 2026-06-17T00:00:00Z
**Status:** draft

## Current State

The pipeline has **no structured event emission today** — phase transitions are marked only by free-text `log(...)` calls (an injected, possibly no-op harness global) and by the boolean return of `runPhase` in `.claude/workflows/qrspi-batch.js` (ref: Q1). The natural transition hooks all live in `runPhase`: phase_start at the top after the reuse short-circuit, phase_failure on the `res === null` and `!p.ok` branches, and phase_success only after `persistArtifact` succeeds — persistence is the single success gate (ref: Q1, Q2). Phase agents write artifacts to a token-free staging path `/tmp/phase-stage/<id>/<name>.md` which `qrspi_persist.py` verifies non-empty and `shutil.move`s to the canonical dest (ref: Q2).

**No trace/span concept exists.** The only cross-cutting correlation id is `runId`, computed once per invocation from `QRSPI_RUN_ID` or `crypto.randomUUID()` (timestamps are forbidden in workflow JS because they break resume), and it is passed today only to the metrics appender (ref: Q3). Ticket context flows JS→Python purely as explicit CLI flags (`--ticket`, `--run-id`); there is no shared context object, env-carried trace, or parent/child span linkage (ref: Q3, Q15).

The self-locating script convention is uniform across `qrspi_persist.py`, `qrspi_metrics_append.py`, `qrspi_resolve.py`, `qrspi_config.py`: `ENGINE_ROOT` from `__file__`, host root via `qrspi_paths.resolve_repo_root(validate=False)` (git-common-dir-first, so the MAIN checkout even from a worktree), short-token argparse flags, a pure I/O-free core plus thin I/O shell, and one JSON envelope `{ok, ..., error?}` on stdout (ref: Q4). One exception: `qrspi_config.py` self-locates via `Path(__file__).resolve().parents[1]` instead, a latent worktree-vs-main divergence (ref: Q4, Inconsistencies).

Configuration has **two single-top-level-key-only readers** with no dot-path support: Python `qrspi_config.read_config()` returns `{}` on any error and never raises, and JS `parseConfigEnvelope` rejects any non-string value (ref: Q5). The example config already nests a `critics` block read by a dedicated resolver `qrspi_critics_config.py` — the established precedent for a nested config block — while `load_ci_revise_cap` shows the simpler "read parsed dict directly + coerce" path for a flat key (ref: Q5, Q6).

The **exponential-backoff retry policy the ticket references "already defined in the pipeline config" does not exist** (ref: Q7). The pipeline's explicit posture is the opposite — fail-closed, report-once, never-retry (ref: Q7, Discovered Patterns). The only backoff in the repo is in `scripts/grade.py`, the eval-judge harness documented as a non-functional placeholder. The only bounded-retry mechanism is the `CI-Revise-Attempt: N` head-commit trailer: a consecutive-red-CI integer counter read by `qrspi_pr_state.ci_revise_attempt`, written exclusively by the orchestrator (`doRevise` → `qrspi_ci_revise_bump.py`), capped by `ciReviseCap` (default 3) — a count, not timed backoff (ref: Q7, Q8).

The closest existing write precedent is `qrspi_metrics_append.append_line` — a JSONL appender that does `os.makedirs(..., exist_ok=True)`, `open(path, "a")` + `write(json.dumps(line) + "\n")` inside a `with` (close-flush), then re-verifies non-empty; it uses no `fsync`, `flock`, or atomic rename (ref: Q9). It also stamps `ticketId`/`timestamp`/`runId` onto every line, appender-wins over caller values (ref: Q15). **No file locking or concurrency guard exists anywhere**; concurrency safety is achieved structurally by per-ticket worktree isolation (`critic-metrics.jsonl` is per-ticket for exactly this reason) (ref: Q11). The only atomicity primitive in the repo is one `os.replace(tmp, path)` in `qrspi_clear_stale_pr.py`, a whole-file cache write (ref: Q9, Q11). Directories are created lazily at write time via `os.makedirs(..., exist_ok=True)`; an unwritable path fails at the write and is reported `ok:false` (ref: Q10).

Validation is done by stdlib `argparse choices=[...]` enums and small hand-rolled coercion helpers (e.g. `coerce_cap`); **`jsonschema` is not used in Python anywhere**, and no `.qrspi/*schema*.json` file exists (ref: Q12). There is **no leveled logging, no `cli.log`, and no `QRSPI_LOG_LEVEL` env var today** — pipeline scripts emit only a single JSON envelope to stdout (reserved for the JS parser), and the few stderr writes that exist are ad-hoc, level-free, and confined to non-pipeline/eval tools (ref: Q14). The unit-test convention is stdlib-only `unittest` `*_test.py` siblings exercising pure helpers against `tempfile` dirs, auto-discovered by `run_tests.py` globbing `scripts/*_test.py` and run in CI (ref: Q13).

## Desired End State

Each acceptance criterion maps to concrete behavior:

- **Phase-gate events for every phase with correct event_type and status** — `runPhase` emits `phase_start` before the agent runs, `phase_success`/`phase_end` after `persistArtifact` returns `ok`, and `phase_failure`/`phase_skip` on the failure/reuse branches, via a thin JS shim that shells to the new Python emitter (ref: Q1, Q2).
- **Append-only, append-aligned JSON lines to the configured log path** — a new `qrspi_event_emit.py` generalizes `qrspi_metrics_append.append_line`: one `json.dumps(event) + "\n"` per `open(path, "a")` close-flush, non-empty re-verify, fail-closed (ref: Q9).
- **Every error generates an `error` event with message and error_code** — emitter accepts `--event-type error` with `error_code`/`message`/optional `traceback` in `context`; failure call sites in `runPhase` and the action dispatchers emit it (ref: Q1).
- **Every retry generates `retry` and `error_retry` events with attempt count and backoff** — see Open Questions OQ1; with no backoff policy existing, retry events are wired to the **only** real retry surface (the CI-revise loop), sourcing `retry_attempt` from the `CI-Revise-Attempt` trailer and reporting `backoff_seconds` as null/absent until a policy exists (ref: Q7, Q8).
- **Log rotation at configured size; old files compressed** — `qrspi_log_rotate.py` checks size against `observability.logSizeThreshold` (default 10 MB), renames the rolled file, gzip-compresses it into `archive/` (ref: Q9, Q10).
- **Retention cleanup: files older than retention archived then removed** — `qrspi_log_retention.py` removes archived files older than `observability.logRetentionDays` (default 30) (ref: Q10).
- **CLI structured logging: all commands emit to cli.log and optionally stderr** — a shared `qrspi_logging.py` helper configures a `logging` logger from `QRSPI_LOG_LEVEL`, writing structured JSON lines to `cli.log` always and stderr at info+ in interactive mode (ref: Q14).
- **Log-level filtering: debug-only fields excluded at info/warn/error** — the logger filters by level threshold from the env var (default `info`) (ref: Q14).
- **Unit tests cover emitter, rotator, retention cleaner** — `*_test.py` siblings against temp dirs, auto-discovered (ref: Q13).
- **Event schema documented and enforceable by a JSON schema file** — a `.qrspi/schema/events.schema.json` file plus a pure-Python validator (since `jsonschema` is absent), reusing the `argparse choices`/coercion enum pattern (ref: Q12).

Context fields (`ticket_id`, `phase`, `trace_id`) are always stamped onto every event/log line by the emitter, appender-wins, mirroring `wrap_envelope` (ref: Q15). `trace_id` is introduced as a new field derived from `runId` (ticket-lifetime span); `span_id`/`parent_span_id` are generated per operation with `crypto` in JS (no timestamps) and passed as flags (ref: Q3, Q15).

## Delta

New Python scripts under `scripts/` (each self-locating per the triad convention, pure core + I/O shell, JSON envelope on stdout, with `*_test.py` siblings): `qrspi_event_emit.py` (the JSONL event appender), `qrspi_log_rotate.py` (size-triggered rotate + gzip to archive), `qrspi_log_retention.py` (age-based archive cleanup), `qrspi_logging.py` (shared leveled-logger factory for the CLI sink), `qrspi_observability_config.py` (dedicated resolver for the nested `observability.*` block, modeled on `qrspi_critics_config.py`), and `qrspi_event_schema.py` (pure validator over the event enums) (ref: Q4, Q5, Q9, Q12, Q13).

New data files: `.qrspi/schema/events.schema.json` (the documented, enforceable schema) and an `observability` block added to `.qrspi/config.example.json` paralleling the `critics` block, each key with a `$comment` sibling (ref: Q6, Q12).

Modified files: `.claude/workflows/qrspi-batch.js` — add an `emitEvent(...)` JS shim and call it at the `runPhase` start/success/failure/skip hooks and at the per-ticket action-dispatch sites; wire `trace_id`/`span_id` generation alongside `runId`; route retry events through `doRevise`'s existing CI-revise counter (ref: Q1, Q3, Q8). New runtime dirs created lazily: `.qrspi/observability/` and `.qrspi/observability/archive/` (ref: Q10). Test runner and CI need no change — they auto-discover the new `*_test.py` siblings (ref: Q13).

## Pattern Decisions

### Decision 1: Event log location — shared vs per-ticket

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Single shared `.qrspi/observability/events.jsonl` (ticket literal path) | Matches ticket text; one log to tail | NEW concurrency surface — no lock exists; concurrent worktrees race the same file (ref: Q11) |
| B | Per-ticket `.worktrees/<id>/.qrspi/<id>/events.jsonl`, mirroring `critic-metrics.jsonl` | Inherits worktree-isolation safety for free; zero new locking | Diverges from the literal ticket path; requires a merge/aggregation step to get one global view |

**Recommendation:** Option B for the durable per-ticket log, with the literal `.qrspi/observability/events.jsonl` path treated as a configurable default for any single-ticket/serial run.
**Rationale:** The pipeline's entire concurrency model is per-ticket worktree isolation with no locks (ref: Q11, Discovered Patterns); a shared append target would be the only unguarded cross-worktree write in the repo. Per-ticket inherits safety exactly as `critic-metrics.jsonl` does.
**NEW PATTERN?** No — reuses the per-ticket-ledger isolation pattern. The literal shared path must be resolved with a human (OQ2).

### Decision 2: Crash-safe append durability

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `O_APPEND` + close-flush + non-empty verify (copy `append_line`) | Exact existing precedent; zero new machinery (ref: Q9) | No `fsync` — a power-loss crash mid-flush can lose the last line |
| B | Add `fh.flush()` + `os.fsync()` per event | True crash-safety the ticket implies | No precedent in the repo; per-line fsync cost; still single-line atomic only |

**Recommendation:** Option A as the baseline, with Option B's `flush()+fsync()` added behind the emitter's single write path since the ticket explicitly says "flushed before continuing."
**Rationale:** `append_line` is the closest analog and is the proven pattern (ref: Q9, Discovered Patterns); a single-line JSONL write under `O_APPEND` is the atomicity unit. Adding fsync is a contained, testable upgrade localized to one helper.
**NEW PATTERN?** Yes (the `fsync` part) — justified because no existing writer offers durability beyond close-flush and the ticket requires "crash-safe ... flushed before continuing" (ref: Q9, Inconsistencies).

### Decision 3: Reading the nested `observability.*` config

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Extend the flat `--key` / `parseConfigEnvelope` path | Reuses one reader | Impossible — JS rejects non-string values; no dot-path (ref: Q5) |
| B | Dedicated `qrspi_observability_config.py` resolver returning a typed envelope, modeled on `qrspi_critics_config.py` | Matches the `critics` precedent; defaults-on-omission; per-key coercion | One more script to maintain |

**Recommendation:** Option B.
**Rationale:** `critics` is read this exact way and `observability` directly parallels it (ref: Q5, Q6). The `--key` path is structurally incapable of carrying nested objects.
**NEW PATTERN?** No — direct reuse of the dedicated-nested-resolver pattern.

### Decision 4: Event-schema enforcement

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add the `jsonschema` library + a JSON Schema file | Standard, declarative | New third-party dep; `jsonschema` is used nowhere; stdlib-only test convention (ref: Q12, Q13) |
| B | Ship `events.schema.json` as documentation + a pure-Python validator over `argparse choices`-style enums | Matches existing validation idiom; stdlib-only; testable | Schema file and validator must be kept in sync |

**Recommendation:** Option B.
**Rationale:** The repo validates via `argparse choices` enums and hand-rolled coercion, never `jsonschema` (ref: Q12). The schema file satisfies "documented and enforceable" while the validator stays stdlib-only per the test convention (ref: Q13).
**NEW PATTERN?** No — reuses enum/coercion validation; the schema file is a new artifact but not a new mechanism.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Retry events specified against a non-existent backoff policy (Q7) lead to fabricated/empty fields | high | med | Wire retry events to the real CI-revise counter only; emit `backoff_seconds` as null until a policy exists; escalate via OQ1 before building |
| Shared `events.jsonl` becomes an unguarded cross-worktree race (Q11) | med | high | Default to per-ticket log (Decision 1); only a serial/single-ticket run writes the shared path; no new lock invented |
| `trace_id`/`span_id` introduced as greenfield (Q3) drift from `runId` or use forbidden `Date.now()` | med | med | Derive `trace_id` from `runId`; generate spans with `crypto` only, mirroring the runId fallback chain; pass as explicit flags |
| Emitter or logger writes to stdout and corrupts the JSON envelope parsed by JS (Q14) | med | high | Events/logs go to file + stderr only; stdout reserved for the `{ok,...}` envelope; covered by a test asserting clean stdout |
| `qrspi_config.py`'s `parents[1]` self-location resolves to the worktree, not main (Q4) | low | med | New `observability` resolver uses `qrspi_paths.resolve_repo_root(validate=False)` like the triad, not the `qrspi_config.py` idiom |
| `STAGE_ROOT`-style duplicated constants (path, threshold) drift across JS and Python (Q2) | med | low | Single-source the threshold/paths through the `observability` resolver envelope consumed by JS, not re-hard-coded |

## Open Questions

- OQ1: The ticket mandates `retry`/`error_retry` events that "follow the exponential-backoff policy already defined in the pipeline config," but no such policy exists — the pipeline is fail-closed/never-retry and the only retry surface is the integer `CI-Revise-Attempt` trailer (ref: Q7, Q8). Should this ticket (a) emit retry events only for the CI-revise loop sourcing the trailer count with `backoff_seconds` omitted, or (b) introduce a new backoff policy config block as part of this work?
- OQ2: The ticket's literal path `.qrspi/observability/events.jsonl` is a single shared file, but the pipeline's only concurrency model is per-ticket worktree isolation with no locking (ref: Q11). Is per-ticket partitioning acceptable, or is a globally shared log a hard requirement (which would need a new locking mechanism to be designed)?
- OQ3: The ticket requires `trace_id`/`span_id`/`parent_span_id` (a full span tree), but the codebase has only a single flat `runId` (ref: Q3). Is a real nested span hierarchy required now, or is stamping `trace_id = runId` plus a per-operation `span_id` (no deep parent chains) sufficient for this foundational ticket?
- OQ4: Should the CLI structured-logging sink (`cli.log`, `QRSPI_LOG_LEVEL`) cover the JS orchestrator's injected `log()` calls too (ref: Q14), or is this ticket scoped to the Python script entry points only, with the JS `log()` wrapping deferred to a follow-up?
