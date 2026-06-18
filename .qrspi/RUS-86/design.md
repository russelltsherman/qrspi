# Design — Structured phase-gate event log: systematic logging for the qrspi review-gate pipeline

**Ticket:** RUS-86
**Research basis:** research.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Current State

The pipeline has **no structured event log today**; the only durable machine-readable per-step record is the critic-metrics JSONL ledger (ref: Q1, Q14). Phase transitions are driven entirely from the JS orchestrator `.claude/workflows/qrspi-batch.js`: a `switch` on the resolver's decision dispatches `do*` handlers, and `runPhase()` is the real per-phase success/failure gate (spawn agent → optional critic stages → persist) (ref: Q1). The JS sandbox cannot do file I/O or run Python directly — it delegates via `agent()` worker prompts and shell-outs through `engineCmd('scripts/...')` (ref: Q1, Q6).

There is **no trace/span model**; the closest concept is `runId`, a single per-invocation id computed once at the top of `qrspi-batch.js` (`QRSPI_RUN_ID` env → `crypto.randomUUID()` → `crypto.getRandomValues` hex → `'run-fallback'`), and `Date.now()`/`Math.random()` are explicitly forbidden for resume safety (ref: Q2). At each transition `ticket_id` is available as `t.id`, `phase` exists in two forms — lowercase machine values (`design|plan|implementation`) from the resolver and Titlecase display labels — and there is **no `actor` field**; the nearest proxy is the `agent()` `label`/`agentType` (ref: Q3).

Config is **single-flat-top-level-key only** (`scripts/qrspi_config.py`); the one nested block (`critics.*`) has a purpose-built resolver (`qrspi_critics_config.py`) rather than a generic dot-path reader (ref: Q4). Env vars are read rarely and inline — defensively `typeof`-guarded in JS, `os.environ.get(...)` with default in Python — and there is **no existing `QRSPI_LOG_LEVEL` or any log-level vocabulary** (ref: Q5). There is **no single CLI entry point**: qrspi is dispatched via slash-command skills, ~40 standalone self-locating `scripts/qrspi_*.py` tools, and JS workflows; a logger "attached to every command" has no chokepoint and must be a shared importable helper (ref: Q6).

The ticket's premise that an "exponential-backoff retry policy [is] already defined in the pipeline config" is **inaccurate**: the only retry mechanism is the CI-revise *cap counter* (a `CI-Revise-Attempt: N` git trailer, no delay/backoff seconds), and the only real exponential backoff lives in the isolated eval harness `grade.py` with module-level (non-config) constants (ref: Q7). `.qrspi/` is only *selectively* gitignored (`config.json`, `features/`, `.worktrees/`); a repo-root `.qrspi/observability/` would be **git-tracked unless a new `.gitignore` entry is added**, and dirs are created lazily via `os.makedirs(..., exist_ok=True)` at first write (ref: Q8). The lone JSONL writer (`qrspi_metrics_append.py`) writes one `json.dumps(line)+"\n"` but does **no flush/fsync** (no `fsync` anywhere in the repo) and has **no atomic-append or partial-line guarantee** (ref: Q9). Concurrency is handled by **path isolation, not locks** — every ticket gets its own worktree and per-ticket `.qrspi/<id>/` sink, the batch loop is sequential, and there is zero lock/`flock` machinery (ref: Q10). There is **no log rotator, size threshold, or compression logic at all** (ref: Q11). Tests are **stdlib-only `unittest` `_test.py` siblings** discovered by `scripts/run_tests.py` and gated in CI with no dependency-install step (ref: Q12). There are **no JSON schema files and no `jsonschema` dependency**; in-repo "schema" means inline JS StructuredOutput objects, and Python validation is hand-rolled `isinstance`/type guards (ref: Q13).

## Desired End State

Each acceptance criterion maps to concrete behavior:

- **Phase-gate events for every phase, correct event_type/status** — A shared Python emitter module appends one JSONL event per transition. The orchestrator shells out to the emitter at the `switch` dispatch (`phase_start`), each `do*` return (`phase_success`/`phase_failure`/`phase_skip`), and `doRevise`'s counter bump (which emits the `retry` event type, carrying the `retry_attempt` field) (ref: Q1). Both `event_type` and `status` are validated against fixed enums: the `event_type` enum is `phase_start`, `phase_end`, `phase_success`, `phase_failure`, `phase_skip`, `error`, `retry`, `error_retry` (the documented superset — see OQ3); the `status` enum is exactly `ok`, `error`, `skipped` (from the ticket schema). The `status`→`event_type` mapping is: `phase_success`/`phase_start`/`retry` carry `ok`; `phase_failure`/`error`/`error_retry` carry `error`; `phase_skip` carries `skipped`. `phase_end` is reserved in the enum as a generic terminal marker but is **not emitted by the batch loop today** — the `do*` returns map to the more specific `phase_success`/`phase_failure`/`phase_skip` (OQ3); it is documented so external/non-batch emitters can use it.
- **Append-only, append-aligned JSON lines to configured path** — The emitter opens in `"a"` mode and writes exactly one `json.dumps(event)+"\n"`, defaulting to `.qrspi/observability/events.jsonl`, mirroring the metrics-ledger writer's append idiom (ref: Q9, Q14) — **with one durability addition on top**: the emitter follows the write with an explicit `flush()`+`os.fsync()` (the ledger writer does neither, ref: Q9) so the last line is not truncated on a crash. This fsync is net-new behavior beyond the ledger precedent (see the Risk Register and the `qrspi_event_log.py` Delta entry).
- **Every error → `error` event with message + error_code** — Error-path call sites emit an `error` event carrying `message`, `error_code`, and optional `traceback` in `context`.
- **Every retry → `retry` + `error_retry` with attempt count and backoff** — Retry events derive `retry_attempt` from the `CI-Revise-Attempt` trailer; `backoff_seconds` has **no pipeline source** and is recorded as `0`/null with an Open Question (ref: Q7).
- **Log rotation at configured size, old files compressed** — A new rotator checks `os.path.getsize` before each event write; when ≥ `observability.logSizeThreshold` (default 10 MB) it renames the active file into `archive/` with a deterministic suffix and gzips it (ref: Q11).
- **Retention cleanup: files older than retention archived then removed** — A retention cleaner removes archived files older than `observability.logRetentionDays` (default 30), invoked at run start.
- **CLI structured logging to cli.log and optionally stderr** — The shared logger writes JSON lines to `.qrspi/observability/cli.log` and, when interactive/at level, also emits to **stderr only** (never stdout, to avoid corrupting the JSON envelopes the orchestrator parses) (ref: Q14).
- **Log level filtering, debug-excluded at higher levels** — Level resolved from `QRSPI_LOG_LEVEL` env → `observability.logLevel` config → `info`, using an ordinal map; below-threshold records are dropped (ref: Q5).
- **Context always includes ticket_id, phase, trace_id** — Every emitted record carries these three; `trace_id` spans the ticket lifetime (ref: Q3).
- **Unit tests cover emitter, rotator, cleaner** — Three stdlib-only `_test.py` siblings, temp-dir based, discovered by `run_tests.py` (ref: Q12).
- **Event schema documented and enforceable by a JSON schema file** — A committed `events.schema.json` plus a stdlib hand-rolled validator (no `jsonschema` dependency) the tests use (ref: Q13). The schema pins both enums explicitly: `event_type` ∈ {`phase_start`, `phase_end`, `phase_success`, `phase_failure`, `phase_skip`, `error`, `retry`, `error_retry`} and `status` ∈ {`ok`, `error`, `skipped`}.

## Delta

New files (under `scripts/`, following the self-locating stdlib convention, ref: Q6):
- `qrspi_event_log.py` — event emitter: builds the event dict, resolves path, calls rotator pre-write, appends one JSON line, then `flush()`+`os.fsync()` (durability addition beyond the ledger precedent — see the append-only End State bullet and the Risk Register); thin CLI + importable helpers. `qrspi_event_log_test.py`.
- `qrspi_log_rotate.py` — size check, rename-into-`archive/`, gzip. `qrspi_log_rotate_test.py`.
- `qrspi_log_retention.py` — age-based archive cleanup. `qrspi_log_retention_test.py`.
- `qrspi_cli_logger.py` — leveled JSON logger (cli.log + optional stderr), level resolution. `qrspi_cli_logger_test.py`.
- `qrspi_observability_config.py` — purpose-built nested `observability.*` reader (mirrors `qrspi_critics_config.py`). `qrspi_observability_config_test.py` (ref: Q4).
- `qrspi_event_schema.py` — fixed enums + hand-rolled stdlib validator. `qrspi_event_schema_test.py` (ref: Q13).
- `.qrspi/observability/events.schema.json` — committed schema document (ref: Q13).

Modified files:
- `.claude/workflows/qrspi-batch.js` — shell-out event emission at the dispatch `switch`, each `do*` return, and `doRevise` bump; trace/span id generation alongside `runId` using the same crypto-guarded, no-timestamp pattern (ref: Q1, Q2).
- `.gitignore` — add commented entries ignoring `.qrspi/observability/events.jsonl`, `cli.log`, and `archive/` (runtime artifacts), keeping `events.schema.json` tracked (ref: Q8).
- `.qrspi/config.example.json` — document the `observability.*` block.

## Pattern Decisions

### Decision 1: Where event emission attaches

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Python emitter module, orchestrator shells out at transition points | Matches "JS delegates to Python" + self-locating tool conventions (ref: Q1, Q6); reusable by skills/scripts | One subprocess per event |
| B | Emit inline in JS, batch-flush | Fewer subprocesses | JS sandbox cannot do file I/O (ref: Q1); breaks the delegation contract |

**Recommendation:** Option A
**Rationale:** The JS sandbox cannot write files; every durable record today goes through a Python shell-out (the metrics ledger, ref: Q14). A shared importable Python emitter is the only option that also serves the per-script CLI logging requirement (ref: Q6).
**NEW PATTERN?** No — it directly mirrors `qrspi_metrics_append.py` (ref: Q9, Q14).

### Decision 2: Event log location and concurrency

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Single repo-root `.qrspi/observability/events.jsonl` | Matches ticket's literal path; one place to read | Breaks path-isolation concurrency model; needs new locking (ref: Q10) |
| B | Per-worktree path, then run-start aggregation to repo root | Inherits existing isolation for free (ref: Q10) | Extra merge step; diverges from ticket's stated path |
| C | Repo-root path + `fcntl.flock` advisory lock around append/rotate | Honors ticket path; safe across concurrent batch invocations | New lock machinery (no precedent, ref: Q10); flock is POSIX-only |

**Recommendation:** Option C
**Rationale:** The ticket explicitly names a single `.qrspi/observability/events.jsonl` and a single rotation/retention target, which Option B's per-worktree split would not honor. Today's sequential single-process loop means contention is rare (ref: Q10), but rotation + a shared path reintroduce a race the codebase has never guarded; a stdlib `fcntl.flock` around the append-and-rotate critical section is the minimal correct guard.
**NEW PATTERN?** Yes — there is zero locking anywhere today (ref: Q10). Justified: path isolation cannot apply to a deliberately shared, rotating log.

### Decision 3: Trace/span id generation

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | crypto-guarded ids in JS (like `runId`), passed to the emitter shell-out | Resume-safe; reuses proven pattern (ref: Q2) | trace_id must be ticket-stable, not run-stable |
| B | Derive trace_id from `ticket_id`, generate span_id per call | Naturally ticket-scoped; deterministic trace_id | Needs a stable per-call span generator |

**Recommendation:** Option B for `trace_id` (derive from `ticket_id`, which spans the ticket lifetime per ticket schema), Option A's crypto-guarded pattern for `span_id`/`parent_span_id`.
**Rationale:** `runId` is run-scoped, not ticket-scoped, so it cannot be `trace_id` directly (ref: Q2). The ticket requires `trace_id` to span the **full ticket lifetime**, and `ticket_id` is the only ticket-stable id available (ref: Q3).
**WHERE span ids are minted:** `trace_id` needs no generation — it is `ticket_id` verbatim, so it is set wherever the event is built. `span_id`/`parent_span_id` are minted **in the Python emitter** (`qrspi_event_log.py`, Decision 1 Option A) using `uuid.uuid4()` / `secrets.token_hex(8)` — a clock-independent, randomness-only stdlib call. The "crypto-guarded, no-`Date.now()`/`Math.random()`" framing comes from the JS `runId` idiom, but that specific prohibition is scoped to the **JS workflow sandbox** (documented at `qrspi-batch.js:115-117); it does **not** bind a Python subprocess. The Python stdlib ids satisfy the same resume-safety property (no wall-clock, no non-crypto PRNG) without importing the JS rule. If a transition needs an id generated on the JS side before the shell-out, it reuses the existing `crypto.randomUUID()` → `crypto.getRandomValues` chain (never `Date.now()`/`Math.random()`).
**NEW PATTERN?** Yes — no trace/span model exists (ref: Q2). Justified by the schema requirement; built on the existing crypto-guarded id idiom.

### Decision 4: Config reader and schema validation

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Purpose-built `observability.*` nested reader (mirror `qrspi_critics_config.py`) + hand-rolled stdlib validator | Matches the established nested-block precedent (ref: Q4) and stdlib-only test contract (ref: Q12, Q13) | Two hand-written validators |
| B | Generalize `qrspi_config.py` to dot-paths + add `jsonschema` dep | Reusable; standards-based validation | Breaks single-key contract and stdlib-only CI (ref: Q4, Q13) |

**Recommendation:** Option A
**Rationale:** The codebase's one nested config block already uses a dedicated resolver rather than a dot-path reader (ref: Q4), and CI has no dependency-install step, so `jsonschema` would break the regression gate (ref: Q12, Q13). The committed `events.schema.json` satisfies the "enforceable by a JSON schema file" AC as a documentation+contract artifact, validated in tests by a stdlib parser.
**NEW PATTERN?** No — `qrspi_critics_config.py` is the precedent for the reader; hand-rolled `isinstance` validation is the precedent for shape checks (ref: Q4, Q13).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `backoff_seconds` has no pipeline source; the ticket premise is wrong (ref: Q7) | high | med | Record `0`/null, document the gap; escalate as OQ1 — either drop the field or define a real backoff policy |
| Shared rotating log reintroduces a concurrency race the codebase never had (ref: Q10) | med | high | `fcntl.flock` around append+rotate (Decision 2); fail-closed if lock unavailable |
| Per-event subprocess on a hot path (every transition) adds latency/overhead (ref: Q1) | med | med | Keep emitter minimal; batch within a `do*` return where possible; measure in e2e |
| stderr logging corrupts stdout JSON envelopes the orchestrator parses (ref: Q14) | med | high | Hard rule: logs to stderr/cli.log only, never stdout; covered by a test asserting clean stdout |
| New `.qrspi/observability/` accidentally git-tracked (ref: Q8) | med | low | Add commented `.gitignore` entries for runtime files; keep schema file tracked |
| No flush/fsync → truncated last line on crash (ref: Q9) | low | med | Add explicit `flush()`+`os.fsync()` in the emitter (new behavior beyond the ledger precedent) |
| Phase vocabulary split (lowercase machine vs Titlecase display) yields inconsistent `phase` values (ref: Q3) | med | low | Standardize on the resolver's unit-tested lowercase machine phase; map at the emitter boundary |
| Ticket `phase` enum (`research`,`structure`,`worktree`,`pr`,`batch`) exceeds the 3 machine phases (ref: Q3) | med | low | Accept the documented superset in the schema; only design/plan/implementation fire from the batch loop today |

## Open Questions

- OQ1: `backoff_seconds` and a config-driven exponential-backoff retry policy do not exist (ref: Q7). Should we (a) drop `backoff_seconds`/`error_retry` from scope, (b) record `retry_attempt` from the `CI-Revise-Attempt` trailer with `backoff_seconds=0`, or (c) introduce a real backoff policy as separate work? **Recommended default (per advisory review): option (b)** — it preserves the ticket's literally-named schema fields (`error_retry`, `backoff_seconds`) and AC wording while honestly recording `backoff_seconds=0`/null because no pipeline source exists; (c) is correctly ruled out as out-of-scope net-new work by Q7's evidence. The design proceeds on (b) above; this remains flagged for explicit human sign-off because dropping vs. null-placeholdering an AC-named field is a product judgment, not a code-derivable fact.
- OQ2: The ticket names a single repo-root `events.jsonl`, but the concurrency model is per-worktree path isolation (ref: Q10). Confirm the shared-path + flock approach (Decision 2 Option C) versus a per-worktree log with aggregation.
- OQ3: The ticket's `phase` enum and `event_type` enum exceed what the batch loop emits today (only design/plan/implementation; no `research`/`structure`/`worktree`/`pr` transitions in the orchestrator) (ref: Q1, Q3). Should the schema document the full superset while only a subset fires now?
- OQ4: "all qrspi CLI commands emit structured logs" — given there is no single CLI entry point (ref: Q6), is wiring the ~40 scripts + skills in scope for this ticket, or is delivering the shared logger module (adopted incrementally) sufficient for the AC? **Recommended default (per advisory review): deliver the shared importable `qrspi_cli_logger.py` module for incremental adoption, plus wire the orchestrator (`qrspi-batch.js`) transitions** as the highest-value first adopter, and treat the sweeping fan-out of all ~40 standalone scripts/skills as follow-up. Q6 establishes there is no chokepoint to attach to mechanically, so a single ticket touching every entry point is a materially larger, cross-cutting scope; shipping the module + the orchestrator emission satisfies the AC's intent on the hottest path while leaving the literal "all commands" breadth as a scoped follow-up. This remains flagged for explicit human sign-off because what counts as "done" for the literal "all commands" wording is a scope boundary only the ticket owner can set.
