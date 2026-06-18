# Design — Structured phase-gate event log: systematic logging for the qrspi review-gate pipeline

**Ticket:** RUS-86
**Research basis:** research.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Current State

The pipeline has no span/trace concept today — no `parent_span_id`, no span id, no nesting context anywhere (ref: Q1). Phase transitions are signalled only by two injected harness globals, `phase(<label>)` and `log(<string>)`, neither defined in the workflow file, and the per-ticket loop dispatches actions through a `switch` on `r.decision.action` calling per-handler `doDesign`/`doPlan`/`doImplementation`/`doSubmit`/`doRevise`/`doLand` (ref: Q1). The only run-scoped correlation id is `runId`, a single module-level `const` computed once with precedence `QRSPI_RUN_ID` env → `crypto.randomUUID()` → hex fallback → `'run-fallback'`, threaded into nested writes via `--run-id '${runId}'` (ref: Q2). The forbidden `Date.now()`/`Math.random()` fallbacks are excluded because they break workflow resume (ref: Q2).

The main checkout's repo root is resolved by `qrspi_paths.resolve_repo_root(repo_root, cwd, validate)`, which prefers the shared `.git` common dir so it yields the main checkout even from a linked worktree; write-side scripts call it with `validate=False` to keep `gh` off the import path (ref: Q3). Every host-mutating script follows the same self-locating convention: `ENGINE_ROOT = dirname(abspath(__file__))`, `sys.path.insert`, a pure-core/thin-CLI split, and one JSON envelope on stdout with `json.dump(env, sys.stdout, indent=2); print()` (ref: Q4). The JS orchestrator never runs Python directly — it spawns an `agent()` whose prompt runs "EXACTLY this one command verbatim" (`engineCmd` for main-cwd, `engineCmdFor(r,...)` for worktree-cwd) and parses the echoed envelope with `extractJsonObject` + `JSON.parse` (ref: Q5).

Configuration is single-top-level-key only — there is no dot-path or nested reader; numeric keys are read via `read_config().get(key)` then a `coerce_*` defensive coercer (e.g. `coerce_cap` rejects bool/float/str/non-positive → default 3), and the JS `parseConfigEnvelope` additionally rejects any non-string value (ref: Q6). The CI gate lives in step "2c" of `resolve()` (`scripts/qrspi_resolve_state.py:274-307`), after unified-feedback and before the active-phase block, evaluating only the frontier phase: red+under-cap → `revise`, red+at-cap → `wait` (`ciGaveUp`), pending → `wait` (ref: Q8). The `CI-Revise-Attempt` trailer is read (`ci_revise_attempt`, last-occurrence-wins, absent→0) and force-reset to 0 whenever CI is not red, but `committedDate` is **never fetched** and the resolver is fully time-agnostic — no clock anywhere (ref: Q7). The cap is read via `load_ci_revise_cap` → `coerce_cap`, defaulted to 3, passed as data into the pure `resolve(state, ci_revise_cap=cap)` (ref: Q9). No clock-injection pattern exists in the resolver test; the established precedent is to pass time as data into the pure function (as `ci_revise_cap` already is) or monkeypatch a module attribute (ref: Q11).

`qrspi_cleanup.py` on `destroy` removes exactly the worktree dir, local `<id>/*` branches, and merged remote refs — it never touches `<root>/.qrspi/` in the main checkout, so a file under `<root>/.qrspi/observability/` survives teardown; the existing critic-metrics ledger lives *inside* the worktree and is therefore destroyed (ref: Q10, Q15). The metrics ledger (`qrspi_metrics_append.py`) is the contrasting precedent: a fail-CLOSED JSONL appender using plain `open(path, "a")` with no fsync/lock/size-cap, one line per process invocation, that errors if the file is empty after write (ref: Q15). There is no precedent for `O_APPEND`/`flock`/`PIPE_BUF`/per-line size caps anywhere in `scripts/`; the metrics appender's safety relies on one-ledger-per-ticket plus sequential ticket processing (ref: Q13). The script stdout channel is fragile — exactly one JSON envelope per script, parsed by the orchestrator — so any logger output must go to stderr or a file, never a script's stdout; several scripts already route diagnostics to stderr (ref: Q12). The test harness (`run_tests.py`) discovers `scripts/*_test.py`, runs each as its own subprocess, and gates CI; two styles (raw-assert table and `unittest.TestCase`) coexist (ref: Q14).

## Desired End State

A new shared, importable, stdlib-only logger module emits structured JSONL observability events for the review-gate pipeline, wired into `qrspi-batch.js` as the first adopter, with a config-driven CI-revise backoff gate added to the resolver. Each acceptance criterion maps as follows:

- **Phase-gate events for every phase with correct `event_type`/`status` and canonical `phase` values** → the emitter writes `phase_start`/`phase_end`/`phase_success`/`phase_failure`/`phase_skip`/`retry`/`error`/`error_retry` events; the orchestrator calls it at each `do*` handler boundary using machine values `design`/`plan`/`implementation` (matching the resolver vocabulary, ref: Q1).
- **Every event carries the required `actor` from its fixed vocabulary** (ticket schema line 30) → each emitted event records an `actor` field drawn from `{<agentType>, batch, cli, user}`: an agent-driven phase transition uses the spawned agent's `agentType`; an orchestrator `do*`-handler decision (the batch loop's own emissions, which are the first-adopter case) uses `batch`; a standalone script that emits via the importable logger uses `cli`; a human-triggered action uses `user`. The first adopter (`qrspi-batch.js`) sources `actor=batch` for every event it emits from a `do*` handler decision, since those emissions are orchestrator decisions, not agent-internal transitions. The emitter takes `actor` as a required caller-supplied argument (it never infers it) and the schema validator enforces the vocabulary. See Decision 5.
- **Append-only, append-aligned, one line per event, per-ticket, in main checkout, surviving teardown, with `flush()`+`os.fsync()`** → events are written to `<root>/.qrspi/observability/<ticket_id>.events.jsonl` via `resolve_repo_root(validate=False)` (ref: Q3), a path outside `.worktrees/` that cleanup never removes (ref: Q10), each event flushed and fsynced before continuing.
- **`parent_span_id` caller-supplied and correctly nested** → the emitter never invents a parent; the orchestrator threads the active phase span's `span_id` into nested critic/retry/command events while a phase span itself carries `null`. A test asserts a nested event's `parent_span_id` equals the enclosing phase's `span_id`.
- **Every error → `error` event with `message` + `error_code`** and **every retry → `retry` + `error_retry` events with `retry_attempt` + `backoff_seconds`** → emitter helpers for these event types; the orchestrator emits them on handler failure / on the CI-revise path.
- **CI-revise backoff policy gates revises** → a new backoff condition in step 2c of `resolve()` defers a still-red frontier to `wait` until `min(base · 2^(attempt-1), cap)` seconds have elapsed since the frontier head-commit `committedDate`, then `revise`; the gather newly fetches `committedDate` and threads it plus a `now` into the pure resolver; `backoff_seconds` is recorded on the `error_retry` event; driven by new top-level `ciReviseBackoffBase`/`ciReviseBackoffCap` keys; resolver-tested with an injected clock (ref: Q7, Q8, Q9, Q11).
- **Log rotation at configurable size with collision-free archive names** and **retention cleanup of old per-ticket files** → a rotator and a retention cleaner module, each unit-tested.
- **CLI structured logging to `cli.log` with a tested contention strategy** → the shared logger writes to `<root>/.qrspi/observability/cli.log` using atomic `O_APPEND` with a hard per-line size cap below `PIPE_BUF` (the documented option from scope), tested for no torn lines under concurrent writers.
- **Every `cli.log` record always carries `ticket_id`, `phase`, and `trace_id`** (ticket line 52 — a hard required-context contract) → the CLI logger's record-building path requires these three keys on every line it writes (the caller supplies `ticket_id`/`phase`; `trace_id` equals `ticket_id` per the trace model, ref: Q1 / ticket line 22), and a unit test asserts each emitted `cli.log` line contains all three. This is a stricter floor than the event emitter's optional `context`: for `cli.log` these three are mandatory, not optional metadata.
- **Log level filtering** → `QRSPI_LOG_LEVEL` (default `info`) overrides `observability.logLevel`; debug-only records excluded at higher levels.
- **Fail-open verified** → a forced write/flush/fsync failure in both emitter and CLI logger returns success and does not raise/halt; stdout stays clean (logs go only to stderr/`cli.log`, ref: Q12).
- **Unit tests cover emitter, rotator, retention cleaner** → `scripts/*_test.py` siblings auto-discovered by `run_tests.py` (ref: Q14).
- **`events.schema.json` is the single source of truth for the `event_type`/`status`/`phase` enums; the hand-rolled validator loads enums from it** → schema file committed; validator reads enums from the file rather than re-hardcoding.

## Delta

New files: `scripts/qrspi_observability.py` (the shared logger module — event emitter taking a required `actor` argument, CLI logger that mandates `ticket_id`/`phase`/`trace_id` on every `cli.log` line, level filtering, fail-open writes, schema-driven validation); `scripts/qrspi_log_rotate.py` (size-triggered rotation with collision-free archive naming); `scripts/qrspi_log_retention.py` (retention archive+remove); `scripts/qrspi_observability_test.py` (covering, among others, that every emitted event carries a valid `actor` and every `cli.log` line carries `ticket_id`/`phase`/`trace_id`), `scripts/qrspi_log_rotate_test.py`, `scripts/qrspi_log_retention_test.py` (siblings, stdlib-only); `scripts/events.schema.json` (source of truth for the `event_type`/`status`/`phase` enums **and** the `actor` vocabulary, and the listing of `actor` as a required field); a new resolver backoff helper test in `scripts/qrspi_resolve_state_test.py`.

Modified files: `scripts/qrspi_pr_state.py` — add `committedDate` to the head-commit GraphQL selection and surface it on the parsed PR node (ref: Q7). `scripts/qrspi_resolve_state.py` — add a pure `backoff_window(base, cap, attempt)` helper and a backoff branch inside step 2c that returns `wait` when elapsed-since-`committedDate` < window, threading `now`/`committed_date` in as data and adding a backoff signal key to the fixed `decision()` key set (ref: Q8). `scripts/qrspi_resolve.py` — load `ciReviseBackoffBase`/`ciReviseBackoffCap` via `read_config().get` + a `coerce_*` defensive coercer mirroring `load_ci_revise_cap`, compute `now`, pass them into `resolve()`, and re-emit the backoff signal at the envelope top level (ref: Q9, Q6). `.claude/workflows/qrspi-batch.js` — emit observability events at each `do*` handler boundary, passing `actor=batch` (every batch emission is a `do*`-handler orchestrator decision, ref: Decision 5), threading the phase `span_id` as `parent_span_id` for nested events and `runId` into `context.run_id`, via the `agent()` + verbatim-command + parse-envelope shape (ref: Q5). `.qrspi/config.example.json` — document the nested `observability.*` block and the two new top-level backoff keys. `.github/workflows/tests.yml` — gated automatically by the existing `run_tests.py` discovery (no edit needed).

Reserved-but-unfired `phase` enum values (`research`, `structure`, `worktree`, `pr`, `batch`) are included in `events.schema.json` for forward compatibility but only `design`/`plan`/`implementation` fire from the batch loop today.

## Pattern Decisions

### Decision 1: How the orchestrator invokes the emitter

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Spawn an `agent()` running `python3 qrspi_observability.py emit ...` verbatim per event, parse envelope (ref: Q5) | Matches the universal script↔worker↔orchestrator contract; reuses `engineCmd`/`engineCmdFor` and envelope parsing | One subagent spawn per event is heavyweight; many events per phase; weak worker may mangle |
| B | Have the orchestrator append the event line directly in JS to the events file | No subagent overhead; lowest latency | Re-implements path resolution + fsync + fail-open in JS, duplicating the Python module; `qrspi-batch.js` is not unit-testable (ref: Q14); diverges from "determinism in self-locating scripts" pattern |

**Recommendation:** Option A
**Rationale:** The repo's hard convention is that the orchestrator never runs Python directly and pushes all determinism into self-locating, unit-tested scripts invoked verbatim via `agent()` (ref: Q5). Reimplementing fsync/path/fail-open logic in the harness-coupled, untestable JS (ref: Q14) would violate that and duplicate the module. The subagent-spawn cost is acceptable because emissions occur at coarse phase boundaries, and fail-open posture means a mangled call is swallowed, not fatal.
**NEW PATTERN?** No — reuses the established `agent()` + verbatim-command + parse-envelope shape (ref: Q5).

### Decision 2: `cli.log` shared-sink contention strategy

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Per-run file `cli.<run_id>.log`, merged-on-read | Mirrors the per-ticket event-log no-lock split; `runId` already available (ref: Q2); no atomicity machinery | More files; a merge-on-read reader must be written; still net-new |
| B | Single `cli.log` with atomic `O_APPEND` (`os.open(O_APPEND)`) + hard per-line size cap below `PIPE_BUF` | One file; POSIX guarantees atomic appends under `PIPE_BUF`; matches the ticket's documented option | No in-repo precedent for `O_APPEND`/`PIPE_BUF` (ref: Q13); net-new mechanism requiring careful testing for torn lines |

**Recommendation:** Option B
**Rationale:** The ticket scope explicitly offers both and Option B keeps a single canonical `cli.log` path matching `observability.cliLog`. No `O_APPEND`/`PIPE_BUF` precedent exists (ref: Q13), so either option is net-new; Option B avoids a separate merge-on-read reader and is directly testable for torn lines under concurrent writers (the AC). The per-line size cap below `PIPE_BUF` is the load-bearing guarantee and must be enforced (truncate/spill oversize records).
**NEW PATTERN?** Yes — atomic `O_APPEND` + sub-`PIPE_BUF` line cap is net-new for this repo (ref: Q13); justified because the existing plain-`open("a")` appender relies on one-writer-per-file + sequential processing (ref: Q13, Q15), an assumption `cli.log` (a shared cross-ticket/phase sink) explicitly breaks (per scope note).

### Decision 3: Threading elapsed time into the pure resolver

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Gather fetches `committedDate`; `resolve()` receives `committed_date` + `now` as data, computes elapsed internally (ref: Q11) | Preserves resolver purity (hard invariant); matches the `ci_revise_cap`-as-data precedent; deterministic test via supplied `now` | Two new threaded inputs; gather + envelope plumbing |
| B | `resolve()` reads the clock itself via `datetime.now()` | Fewer threaded params | Breaks the resolver-is-pure invariant (ref: Q11); untestable without monkeypatching a third-party-free clock; no precedent |

**Recommendation:** Option A
**Rationale:** `resolve()` performs no I/O of its own and `ci_revise_cap` is already injected as data (ref: Q11). The test factories already accept `ci_state`/`ci_attempt` kwargs and would be extended with `committed_date`/`now` the same way RUS-81 extended them (ref: Q11). This keeps the unit test deterministic with an injected clock, which the AC requires.
**NEW PATTERN?** No — extends the existing "pass behavior inputs as data into the pure resolver" pattern (ref: Q9, Q11).

### Decision 4: Reading the nested `observability.*` config block

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | A dedicated `read_observability_config()` helper in `qrspi_config.py` returning the nested dict (Python callers only; not via the string-only CLI envelope) | Localizes nested access; keeps the existing flat `--key` reader untouched; backoff keys stay flat top-level (ref: Q6) | New reader surface to test |
| B | Flatten `observability.*` to top-level keys read via existing `read_config().get` | Reuses the flat reader verbatim | Contradicts the ticket's explicit nested-block schema; pollutes top-level namespace; loses telemetry/behavior separation |

**Recommendation:** Option A
**Rationale:** The reader is single-top-level-key only with no dot-path, and the JS `parseConfigEnvelope` rejects non-string values (ref: Q6) — so the nested block cannot go through the CLI envelope and must be read Python-side. The backoff keys deliberately stay flat top-level (behavior, not telemetry) and follow the `coerce_cap`/`load_ci_revise_cap` numeric pattern (ref: Q9). Project memory `qrspi-config-reader-single-key-only.md` requires the plan to specify this mechanism explicitly rather than assume an existing path.
**NEW PATTERN?** No — adds one helper to the existing config module; the flat numeric-key path for backoff already has a template in `coerce_cap` (ref: Q6, Q9).

### Decision 5: The required `actor` field and where each value is sourced

The ticket's event schema (ticket line 30) makes `actor` a **required** field with a fixed vocabulary — `<agentType>` (agent-driven transition), `batch` (orchestrator decision), `cli` (standalone script), `user` (human-triggered action). It is distinct from `parent_span_id` (nesting) and from `context.run_id` (run correlation): `actor` answers *who performed the action*. It is **not** covered by AC13, which scopes `events.schema.json` as the source of truth only for the `event_type`/`status`/`phase` enums; `actor` is a separate required field that must still be emitted, schema-listed, and validated.

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Emitter requires `actor` as a caller-supplied argument; the orchestrator/script passes the correct vocabulary value per call site | Mirrors the `parent_span_id` "caller supplies, emitter never invents" contract (ref: Q1 / ticket line 24); each call site knows its own actor | One more required arg per emit call |
| B | Emitter infers `actor` from ambient state (e.g. an env var or always `batch`) | Fewer args | Emitter cannot reliably know the actor; collapses the vocabulary; contradicts the schema's four distinct values |

**Recommendation:** Option A
**Rationale:** `actor` parallels `parent_span_id` exactly — a stateless per-event emitter cannot know who triggered the call, so the caller supplies it (ref: Q1 / ticket line 24). Sourcing per call site: the batch loop's `do*`-handler decisions emit `actor=batch` (the orchestrator decided to act); a future standalone script adopting the importable logger emits `actor=cli`; an agent-driven phase transition emits the spawned agent's `agentType`; a human-triggered action emits `user`. For the first adopter (`qrspi-batch.js`) every emission is a `do*`-handler decision, so all of its events carry `actor=batch`. `actor` is added to the event schema's field list and to the hand-rolled validator's required-field check (its vocabulary is closed but, like the other enums, can be sourced from `events.schema.json` so there is one source of truth).
**NEW PATTERN?** No — reuses the established caller-supplies-it contract already used for `parent_span_id` (ref: Q1 / ticket line 24).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Backoff gate is a no-op in practice — it only defers within a resolver pass and does not schedule a wake-up, so it only bites under a tight loop / fast cron (per scope) | high | low | Document the activation regime explicitly; choose defaults (base 300s, cap 3600s) accordingly; the existing cap remains the hard terminator |
| `O_APPEND` + `PIPE_BUF` is net-new with no in-repo precedent (ref: Q13); torn/interleaved lines if the per-line cap is mis-enforced | med | high | Hard-enforce a per-line byte cap below `PIPE_BUF` before write; add a concurrent-writer test asserting no torn lines (an explicit AC) |
| `committedDate` plumbing touches the gather + pure resolver + envelope re-emit; a missing/`null` date could mis-gate a revise | med | med | Treat absent `committedDate` as "elapsed = infinite" (do not defer) so a fetch gap never traps a ticket in `wait`; unit-test the null path |
| Per-event `agent()` spawns add latency/weak-worker fragility at phase boundaries (ref: Q5) | med | low | Fail-open swallows mangled emissions; emit only at coarse phase boundaries, not per log line; keep the verbatim-command contract |
| Adding a key to the resolver's fixed `decision()` key set without re-emitting it at the envelope top level silently drops the backoff signal (ref: Q8) | med | med | Add the key in `decision()` and the matching top-level re-emit in `qrspi_resolve.py` in the same slice; mirror the `ciFailing` plumbing |
| `events.schema.json` enum drift from validator/code (the repo already shows doc/code drift, ref: inconsistencies) | low | med | Validator loads enums from the schema file (an AC) so there is one source of truth; test the validator against the schema |

## Open Questions

- OQ1: For `cli.log`, the ticket offers per-run-file vs `O_APPEND`+`PIPE_BUF`; this design recommends the latter (Decision 2). Confirm that is acceptable, or whether the per-run merged-on-read split is preferred for symmetry with the event log.
- OQ2: When a per-line CLI record exceeds the sub-`PIPE_BUF` cap, should it be truncated (with a marker), dropped, or split across lines? The AC requires no torn lines but does not specify oversize handling.
- OQ3: Should `phase_end` be emitted in addition to `phase_success`/`phase_failure` for every phase, or only as a paired bracket around the span? The schema lists both; the nesting/emission cadence in `qrspi-batch.js` should be pinned in the Structure phase.
- OQ4: The backoff is acknowledged as effectively a no-op unless runs are tightly spaced. Is shipping a non-scheduling within-pass gate (no wake-up) acceptable for this ticket, with scheduling deferred to follow-up under parent RUS-85?
