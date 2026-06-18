# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

> **TOP-LEVEL FINDING (read first):** The questions are premised on a prior ticket
> **RUS-85** having landed an "event-log emission" subsystem that writes
> `.qrspi/observability/events.jsonl` with `phase_start`/`phase_end`/`event_type`
> records. **No such code, file, or directory exists in this worktree.** There is
> no `.qrspi/observability/` directory, no `events.jsonl`, no `event_type` /
> `phase_start` / `phase_end` / `emit_event` symbol anywhere, and no string `RUS-85`
> outside the questions file itself. Every RUS-85-targeted question (Q1, Q2, Q3, Q7,
> Q8-RUS-85-half, Q9, Q10-RUS-85-half, Q12) is therefore **NOT FOUND** as a direct
> answer; where a *precedent pattern* exists (the critic-metrics JSONL ledger
> family) it is cited as the nearest analog. The infrastructure-side questions (Q4,
> Q5, Q6, Q10-resolver-half, Q11, Q13) are answerable from the existing harness.

Search queries run to establish the RUS-85 absence:
`find . -name '*.jsonl'` (only `.qrspi/RUS-*/critic-metrics.jsonl` ledgers);
`grep -rln "event_type\|phase_start\|phase_end\|emit_event\|events\.jsonl"` over
`*.py`/`*.js` → **zero hits**; `grep -rl "RUS-85"` → only `.qrspi/RUS-87/questions.md`;
`ls .qrspi/observability/` → does not exist.

---

## Q1: On-disk schema / field set of each JSON line in `.qrspi/observability/events.jsonl` (RUS-85)

**Answer:** **NOT FOUND.** Neither `.qrspi/observability/` nor `events.jsonl` exists, and
no emitter writes them. There is no `event_type`, `phase_start`, `phase_end`, `error_code`,
or schema definition for such a log anywhere in the tree.

**Nearest existing analog (the only structured JSONL ledger in the repo):** the RUS-77
critic-metrics ledger at `.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`, written one
JSON object per line by `scripts/qrspi_metrics_append.py`. Its envelope (the fields a
consumer can rely on per line) is injected by `wrap_envelope`:

```python
def wrap_envelope(record, ticket, timestamp, run_id):
    line = dict(record)
    line["ticketId"] = ticket          # e.g. "RUS-77"
    line["timestamp"] = timestamp      # UTC ISO-8601, write-time
    line["runId"] = run_id             # orchestrator per-invocation id
    return line
```

— `scripts/qrspi_metrics_append.py:67-79`

So the established per-line shape is `{ ...record, ticketId, timestamp, runId }` — note
the keys are **camelCase** (`ticketId`, not `ticket_id`), which contradicts the snake_case
`ticket_id` / `event_type` / `error_code` the question assumes. There is **no `phase`,
`event_type`, or `error_code` field** in any existing ledger line; the record payload comes
from `qrspi_critic_metrics.build_record` (RUS-77 critic metrics), not a phase-gate event.

**Dependencies:** any consumer would depend on a not-yet-existing RUS-85 writer. The only
real upstream is the camelCase-envelope convention above.
**Implicit contracts:** existing JSONL ledgers are append-only, one JSON object per line,
UTC ISO-8601 timestamps, camelCase keys, written by a self-locating Python CLI that fails
closed on empty.

## Q2: How RUS-85 rotates `events.jsonl` (rename/truncate, size/time trigger, inode/size signal)

**Answer:** **NOT FOUND.** No rotation logic exists because the log itself does not exist.
The existing `critic-metrics.jsonl` ledger has **no rotation at all** — `append_line` opens
in `"a"` mode and appends unconditionally, never renaming, truncating, or size-capping:

```python
def append_line(path, ledger_line):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(ledger_line) + "\n")
    ...
```

— `scripts/qrspi_metrics_append.py:82-99`

There is therefore **no precedent rotation scheme** and **no file-identity (inode/size-shrink)
signal** to reuse. A tailer's rotation-detection design has no existing contract to conform to.

**Dependencies:** none (feature absent).
**Implicit contracts:** the one ledger precedent is *unbounded append* — any rotation is net-new.

## Q3: `phase_start` / `phase_end` pairing in the log (matching keys, ordering) for duration computation

**Answer:** **NOT FOUND.** No `phase_start`/`phase_end` events are emitted anywhere. The
phase lifecycle exists only as the PR-gated state machine (design → plan → slice PRs), and
phase identity is carried in branch names (`<id>/design`, `<id>/plan`, `<id>/slice-N`) and
in the resolver's phase names, **not** in any emitted start/end event with timestamps. The
critic-metrics ledger does carry a `phase` field in its *record payload* (seen in the test
fixture `line["phase"] == "design"` at `scripts/qrspi_metrics_append_test.py:45`) plus a
write-time `timestamp`, but it is one terminal row per critic step — there is **no paired
start/end** and no duration semantics.

**Dependencies:** the resolver's phase vocabulary (`scripts/qrspi_resolve_state.py`) is the
only authoritative phase enumeration; see Q10.
**Implicit contracts:** phase names in this repo are `design` / `plan` / `implementation`
(slices). Any pairing scheme is net-new.

## Q4: Existing CLI command surface a new `qrspi log query` must plug into (subcommand registration, `--table`/`--json`)

**Answer:** **There is no unified `qrspi` CLI binary and no subcommand-dispatch / registration
layer.** There is no `pyproject.toml`, `setup.py`, `setup.cfg`, `bin/`, or `console_scripts`
entry point — confirmed by `ls` (all absent). The harness is a flat collection of
**independent single-purpose Python scripts** in `scripts/`, each invoked directly as
`python3 scripts/<name>.py` with its **own** `argparse.ArgumentParser` and its own flags.
There is **no `add_subparsers`** dispatch anywhere (grep for `add_subparsers` → zero hits).

There is also **no `--table` / `--json` output-format convention.** Every `--json` occurrence
in the tree is a `gh ... --json <fields>` GraphQL field selection (e.g.
`scripts/qrspi_resolve.py:365`, `scripts/qrspi_land_verify.py:79`,
`scripts/qrspi_cleanup.py:107`), not a qrspi output-mode flag. Scripts uniformly emit a
**single JSON envelope on stdout** and signal success via **exit code** — e.g.

```python
parser = argparse.ArgumentParser(description="...")
parser.add_argument("--key", required=True, help="config.json key to resolve")
args = parser.parse_args()
...
print(json.dumps({"ok": True, "key": key, "value": value}))
```

— `scripts/qrspi_config.py:60-71`

**Dependencies:** a `qrspi log query` command would be a net-new standalone
`scripts/qrspi_*.py` following the one-script-one-argparse-JSON-envelope convention; it
cannot "plug into" a dispatcher because none exists.
**Implicit contracts:** every script is self-locating (root from `__file__`), stdlib-only,
prints one JSON object to stdout, exits 0 on success / non-zero on failure, and ships a
`<name>_test.py` sibling.

## Q5: How config is read for nested/dotted paths (`observability.tailInterval`, `observability.alerts.phaseTimeout`) given single-top-level-key readers

**Answer:** **Neither config reader supports dotted/nested paths — both are single-top-level-key
only**, exactly as the question hints. There is **no existing mechanism** to read
`observability.tailInterval`; it would have to be built.

Python side — `scripts/qrspi_config.py` reads exactly one top-level key via `dict.get`, no
dot-splitting:

```python
def select_value(config: dict, key: str, default: str) -> str:
    value = config.get(key)
    return value if value else default
```

— `scripts/qrspi_config.py:36-42` (invoked as `--key linearProject`,
`scripts/qrspi_config.py:63-71`)

JS side — `parseConfigEnvelope` consumes that single-key envelope and **rejects any
non-string value**, so it cannot pass through a nested object:

```js
if (env.key !== key) return { ok: false, error: `config: envelope key mismatch (...)` }
if (typeof env.value !== 'string') return { ok: false, error: `config: envelope value not a string (got ${env.value})` }
```

— `.claude/workflows/qrspi-batch.js:373-374`

Note the precedent for a *would-be-nested* config (`critics.design.maxRounds` in
`.qrspi/config.example.json`) is read by a **separate dedicated resolver**
(`scripts/qrspi_critics_config.py`) rather than by extending `qrspi_config.py` with dot-paths,
and the CI cap was deliberately flattened to a top-level `ciReviseCap` key
(`.qrspi/config.example.json`, `$comment_ci`) to fit the single-key reader. This is the
established pattern: **add a purpose-built resolver per config concern, or flatten the key —
do not assume a generic dotted-path reader exists.**

**Dependencies:** `scripts/qrspi_config.py`, `scripts/qrspi_critics_config.py` (nested-read
precedent), `.claude/workflows/qrspi-batch.js` `parseConfigEnvelope`.
**Implicit contracts:** JS `parseConfigEnvelope` hard-fails on non-string config values; any
new nested observability config must either be flattened or read by its own resolver that
emits the standard `{ok,key,value}` envelope (with `value` stringified) or its own shape.

## Q6: Where the in-memory per-ticket state store would live given the process model (long-running watcher vs short-lived invocation)

**Answer:** **There is no long-running watcher / daemon process. Every entry point is
short-lived and single-pass.** No `while True`, no daemon, no event loop, no tail/inotify
exists (the grep hits for "watch/poll/tail" are all substrings inside comments/test names,
not control flow). The autonomous driver is `.claude/workflows/qrspi-batch.js`, which runs
**one pass** over the ticket set and exits — its top-level control flow iterates ticket
batches once:

```js
for (const b of batches) {
  ...
  for (const t of b.tickets) {
```

— `.claude/workflows/qrspi-batch.js:1631-1633`

State **between** runs is not held in memory; it is **re-derived every invocation** from
external sources of truth: PR review state (`scripts/qrspi_pr_state.py` via `gh` GraphQL),
the resolver (`scripts/qrspi_resolve_state.py`), and on-disk artifacts/ledgers. The CI-revise
counter, for instance, is **not** an in-memory store — it is persisted as a `CI-Revise-Attempt: N`
**git commit-message trailer** and re-read each pass (see CLAUDE.md lifecycle section).

**Implication for the asked design (not an opinion, a structural fact):** an "in-memory
per-ticket state store" with live durations/retry-history has **no host process to live in**
today. Either RUS-87 introduces the first long-running process in the repo, or per-ticket
state must (like every other piece of state here) be recomputed each short-lived invocation
from the durable event log.

**Dependencies:** `.claude/workflows/qrspi-batch.js` (single-pass orchestrator),
`scripts/qrspi_pr_state.py`, `scripts/qrspi_resolve_state.py`.
**Implicit contracts:** the repo's invariant is *stateless re-derivation each run* — durable
state lives on disk (ledgers, artifacts) or in git (trailers, branches), never in a resident
process.

## Q7: Signal in the event log marking a ticket "completed" (for state-store reset)

**Answer:** **NOT FOUND in any event log** (no event log exists). The *lifecycle* notion of
"completed" lives entirely in the PR-gated resolver and Linear status, not in an emitted
terminal event. The resolver computes the terminal advancement; the documented terminal
Linear status is **`Done`** (CLAUDE.md: `Selected → Design Review → Plan Review → Code Review
→ Done`), reached after the whole Graphite stack is approved and landed bottom-up. The
resolver code in `scripts/qrspi_resolve_state.py` decides `land` / advance per-phase but does
**not** emit a "ticket completed" record to any log.

**Dependencies:** `scripts/qrspi_resolve_state.py` (terminal decision), Linear status
projection (best-effort, never authoritative for advancement).
**Implicit contracts:** "completed" = full stack landed → Linear `Done`; this is a
*derived/observed* state, not a logged event today.

## Q8: Tailer handling of a malformed / partially-written JSON line — existing JSONL-reader behavior

**Answer:** The **established, tested pattern for tolerating malformed/truncated JSONL lines**
is in `scripts/qrspi_critic_summary.py._read_lines`: read line-by-line, skip blank lines,
`json.loads` each, and on `json.JSONDecodeError` **skip the line and increment an aborted
counter** (explicitly to tolerate a trailing partial/truncated line); a parsed **non-dict** is
also counted aborted and skipped:

```python
for raw in fh:
    line = raw.strip()
    if not line:
        continue
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        aborted += 1
        continue
    if not isinstance(obj, dict):
        aborted += 1
        continue
    good.append(obj)
```

— `scripts/qrspi_critic_summary.py:55-71`

This is the directly-reusable precedent for the tailer's parse-failure behavior (skip + count,
never raise). On the **writer/atomicity** half of the question: the existing writer
(`qrspi_metrics_append.append_line`, `scripts/qrspi_metrics_append.py:88-90`) does a plain
buffered `open(path, "a")` + `fh.write(json.dumps(...) + "\n")` — **no fsync, no atomic
rename, no advisory lock** — so a partial line during concurrent write is *possible* and the
reader-side skip is exactly what compensates for it. The RUS-85 writer's flush/atomicity
guarantees are **NOT FOUND** (writer absent).

**Dependencies:** `scripts/qrspi_critic_summary.py` (tolerant reader),
`scripts/qrspi_metrics_append.py` (non-atomic appender).
**Implicit contracts:** readers in this repo are expected to be **fault-tolerant by skipping**
malformed lines (the loaders never raise on a bad line); writers are plain buffered appends
with no atomicity guarantee.

## Q9: Behavior when `events.jsonl` is missing / empty / `.qrspi/observability/` absent at start

**Answer:** **NOT FOUND** for the specific log (it and the watcher are absent). The closest
precedent behaviors:

- **Writer** creates the parent dir on demand and fails closed on an empty result:
  `os.makedirs(os.path.dirname(path), exist_ok=True)` then a non-empty verify returning an
  error if `size == 0` — `scripts/qrspi_metrics_append.py:88, 91-96`.
- **Config reader** is best-effort on a missing file: any `OSError`/`ValueError` → `{}` (never
  raises) — `scripts/qrspi_config.py:50-56`.
- The tolerant ledger reader (`_read_lines`, Q8) opens the path directly and would raise
  `FileNotFoundError` if the file is absent — i.e. existing readers assume the file exists by
  the time they read; **there is no "wait for file to appear" / empty-directory startup
  handling anywhere** to reuse.

**Dependencies:** `scripts/qrspi_metrics_append.py`, `scripts/qrspi_config.py`.
**Implicit contracts:** writers create dirs and fail-closed-on-empty; config reads degrade
gracefully to defaults; raw ledger reads assume existence. A "watcher startup against an
absent file/dir" has **no precedent** and is net-new.

## Q10: Timestamp source / clock for events, and any existing phase-timeout / hang detection to reconcile with

**Answer (timestamp source):** The established stamp is **`datetime.now(timezone.utc).isoformat()`**
— UTC, ISO-8601, generated at write time by the appender:

```python
timestamp = datetime.now(timezone.utc).isoformat()
```

— `scripts/qrspi_metrics_append.py:133`

(Wall-clock UTC; no monotonic clock is used anywhere. `scripts/qrspi_order_tickets.py:58-63`
parses incoming ISO timestamps with `datetime.fromisoformat`, tolerating a trailing `Z`.)

**Answer (phase-timeout / hang detection in the resolver):** **NONE EXISTS.**
`scripts/qrspi_resolve_state.py` has **no notion of time, duration, staleness, or hang** — grep
for `timeout|hang|stale|duration|silent|elapsed|now(` over the resolver returns **only the
substring "change request"** (e.g. lines 30, 39-48, 94-107…) and no temporal logic. The
resolver decides purely on **discrete PR signals**: review decision, unresolved threads, CI
rollup (`green|red|pending|none`), and the `CI-Revise-Attempt` cap counter. The only bound
that resembles "stop the loop" is the **consecutive-red CI cap** (`ciReviseCap`, default 3,
`.qrspi/config.example.json` `$comment_ci`) — a *count*-based cap, **not a time/duration-based
one**. So there is **nothing temporal to reconcile a "silent phase" grace period against**; it
would be the first time-based bound in the decision layer.

**Dependencies:** `scripts/qrspi_metrics_append.py` (timestamp convention),
`scripts/qrspi_resolve_state.py` (decision logic — no temporal state),
`scripts/qrspi_order_tickets.py` (ISO-parse precedent).
**Implicit contracts:** all timestamps are UTC ISO-8601 wall-clock; the decision layer is
event/count-driven, never time-driven; `fromisoformat` is the repo's parse path (handles `Z`
on 3.11+ with a documented older-runtime caveat at `qrspi_order_tickets.py:58-63`).

## Q11: Test harness / fixtures for synthetic JSONL lines; how `*_test.py` siblings + `run_tests.py` structure unit tests

**Answer:** The harness is **stdlib `unittest`, one `scripts/<name>_test.py` sibling per
script**, aggregated by `scripts/run_tests.py`, which discovers every `*_test.py` and runs
each as its **own subprocess** (PASS/FAIL per file, non-zero exit if any fails — the CI gate):

```python
def discover_tests(scripts_dir=SCRIPT_DIR, pattern=None):
    names = sorted(n for n in os.listdir(scripts_dir) if n.endswith("_test.py"))
    if pattern:
        names = [n for n in names if pattern in n]
    return [os.path.join(scripts_dir, n) for n in names]
```

— `scripts/run_tests.py:36-48` (runner shape: `run_one` subprocess at lines 51-75,
`DEFAULT_TIMEOUT = 180` per file at line 33). Invoked `python3 scripts/run_tests.py`,
`--list` to enumerate, substring arg to filter.

**Synthetic-line / temp-file fixture precedent** is exactly what the new tailer/state-store/
metrics tests would copy — `scripts/qrspi_metrics_append_test.py` uses `tempfile` and asserts
on the parsed back-read line:

```python
import tempfile
...
def test_injects_envelope_fields(self):
    ...
    self.assertEqual(line["ticketId"], "RUS-77")
    self.assertEqual(line["timestamp"], "2026-06-15T00:00:00+00:00")
    self.assertEqual(line["runId"], "run-A")
```

— `scripts/qrspi_metrics_append_test.py:7, 38-46`

The tolerant-reader test precedent (feeding malformed lines and asserting skip/abort counts)
lives alongside `scripts/qrspi_critic_summary.py` as `qrspi_critic_summary_test.py`. There is
**no shared "JSONL fixture builder" utility** — each test constructs its own lines inline /
in a `tempfile`.

**Dependencies:** `scripts/run_tests.py`, `.github/workflows/tests.yml` (the same command is
the CI regression gate — CLAUDE.md), `scripts/qrspi_metrics_append_test.py` /
`scripts/qrspi_critic_summary_test.py` (closest fixtures).
**Implicit contracts:** stdlib-only (no pytest); each test is a standalone
`python3 scripts/<name>_test.py` exiting 0/non-zero, guarded by `__main__`; pure logic split
into argument-driven helpers so tests exercise them with in-memory dicts / temp dirs; new
work ships its `_test.py` sibling or `run_tests.py` won't cover it.

## Q12: RUS-85 integration setup for producing real emitted events (to drive an end-to-end test from real emission)

**Answer:** **NOT FOUND.** There are no RUS-85 event-emission integration points, and there is
**no real integration-test tier** in the suite to extend. The repo is explicit that
end-to-end coverage is **manual**: CLAUDE.md states "JS coverage of `qrspi-batch.js` is
deferred (the file is harness-coupled…)" and "the `evals/` + `scripts/run_eval.py` harness is
a **non-functional placeholder** — verify pure logic with the unit tests and orchestration
changes with **manual end-to-end runs**." The JS↔Python seam is covered only by **contract
fixtures** (`scripts/qrspi_contract_fixtures_{producer,consumer}_test.py`), not by driving
real subprocesses. So an "emit-then-consume" integration test has **no existing emission
harness to call** — both the emitter (RUS-85) and an integration tier would be net-new, and
the repo convention would push the verifiable core into stdlib unit tests with the e2e path
exercised manually.

**Dependencies:** `scripts/run_eval.py` (placeholder, do not rely on),
`scripts/qrspi_contract_fixtures_*_test.py` (the actual seam-coverage pattern).
**Implicit contracts:** functional core → unit-tested deterministically; orchestration/e2e →
manual; cross-language seams → static contract fixtures rather than live integration.

## Q13: How the "CLI log" alerts write to is implemented (levels warn/error, sink, format); existing structured/JSON logging facility

**Answer:** **There is no logging facility and no `warn`/`error` level abstraction in the
Python scripts.** Grep for `logging.` / `getLogger` / `level=` / `warn(` / `warning(` over
`scripts/` and `qrspi-batch.js` returns only a **test-file substring** hit
(`qrspi_critics_config_test.py`) — i.e. the stdlib `logging` module is **not used anywhere**.
Scripts communicate via two channels only:

1. A single **JSON envelope on stdout** with an `ok` boolean and optional `error` string,
   plus a non-zero **exit code** on failure — e.g.
   `json.dump(env, sys.stdout, ...)` then `return 1` (`scripts/qrspi_metrics_append.py:120-123,
   137-149`); `print(json.dumps({"ok": False, ..., "error": str(exc)}))`
   (`scripts/qrspi_config.py:73-75`).
2. On the **JS orchestrator** side, a `log(...)` helper prints human-readable progress lines
   (e.g. `.claude/workflows/qrspi-batch.js:1673`); there are **no severity levels** — it is
   plain console output.

There is **no structured/JSON application log, no severity taxonomy, and no log sink** that
alert output could "conform to." Any alert-output format (levels `warn`/`error`, a JSON shape)
would be **net-new convention**; the closest existing convention is the `{ok, error?}` JSON
envelope + exit code.

**Dependencies:** `scripts/qrspi_metrics_append.py`, `scripts/qrspi_config.py` (envelope
convention), `.claude/workflows/qrspi-batch.js` (`log()` console output).
**Implicit contracts:** "logging" here = JSON envelope on stdout + exit code (machine) and
unleveled `log()` lines (human); no `logging` module, no level filtering, no file/sink.

---

## Discovered Patterns

- **One-script-one-purpose, stdlib-only, self-locating.** Every `scripts/qrspi_*.py` is a
  standalone CLI with its own `argparse`, resolves the repo root from `__file__` (not cwd/args),
  imports nothing outside stdlib, prints a single JSON envelope on stdout, and ships a
  `<name>_test.py` sibling. There is **no shared CLI framework, no subcommand dispatcher, no
  package/entry-point** (`scripts/qrspi_config.py`, `scripts/qrspi_metrics_append.py`,
  `scripts/run_tests.py`).
- **JSON-envelope-over-exit-code IPC.** Scripts signal success/failure with `{ok, ...,
  error?}` on stdout + exit code; the JS orchestrator parses it (`extractJsonObject` /
  `parseConfigEnvelope`, `.claude/workflows/qrspi-batch.js:366-376`). Used in place of any
  logging or return-channel.
- **The only structured JSONL ledger is the RUS-77 critic-metrics family** — append-only,
  one camelCase JSON object per line, UTC ISO-8601 `timestamp`, written non-atomically by
  `qrspi_metrics_append.py`, read fault-tolerantly (skip+count malformed lines) by
  `qrspi_critic_summary.py`. This is the single reusable precedent for an `events.jsonl`
  tailer/consumer, and its key style is **camelCase**, not the snake_case the questions assume.
- **Stateless re-derivation each run.** No resident process holds state between invocations;
  qrspi-batch is single-pass, and "memory" lives on disk (ledgers/artifacts) or in git (the
  `CI-Revise-Attempt` commit-message trailer, branch names). PR review state is fetched fresh
  every pass.
- **Decision layer is event/count-driven, never time-driven.** The resolver
  (`qrspi_resolve_state.py`) reasons over discrete PR signals (review decision, threads, CI
  rollup) and a *count* cap (`ciReviseCap`); it has zero temporal logic.
- **Config is single-top-level-key.** Both `qrspi_config.py` (Python) and `parseConfigEnvelope`
  (JS, string-only values) reject nesting; nested config is handled by a *dedicated per-concern
  resolver* (`qrspi_critics_config.py`) or by *flattening the key* (`ciReviseCap`).

## Inconsistencies

- **The questions assume a landed RUS-85 event-log subsystem that does not exist** in this
  worktree (no `events.jsonl`, no emitter, no `phase_start`/`phase_end`/`event_type`/`error_code`).
  This is the largest gap: nine of the thirteen questions target absent code. A consumer/tailer
  for `.qrspi/observability/events.jsonl` would be building against a producer that has not
  been written, OR RUS-85 must be treated as a hard upstream dependency of this work.
- **Field-naming mismatch.** Questions Q1/Q3/Q7 reference snake_case fields (`ticket_id`,
  `event_type`, `error_code`, `phase`); the repo's actual ledger convention is **camelCase**
  (`ticketId`, `runId`, `timestamp` — `qrspi_metrics_append.py:75-79`). A consumer assuming
  snake_case keys would not match the established producer style.
- **"CLI log" / "log levels warn/error" (Q13) presupposes a logging facility that does not
  exist.** The repo has no `logging` usage at all — only JSON envelopes + exit codes and an
  unleveled JS `log()`. The premise of conforming alert output to an existing leveled log sink
  is unfounded.
- **`--table` / `--json` output-mode convention (Q4) does not exist.** All `--json` in the tree
  is `gh`'s GraphQL field-selection flag, not a qrspi output-format flag. The premise of a
  table/json toggle convention to plug into is unfounded.
- **No long-running watcher process (Q6) exists**, despite the question offering "long-running
  watcher process" as one of two options — the repo has *only* short-lived single-pass
  invocations, so an in-memory live-duration state store has no host. Either RUS-87 introduces
  the first resident process, or it must follow the repo's stateless-re-derivation invariant.
- **The eval/integration tooling is a documented placeholder** (`scripts/run_eval.py`,
  `report.py`, `diagnose.py` are eval-only and non-functional per CLAUDE.md), so Q12's
  "integration test" has no real harness — contradicting any assumption that an integration
  tier exists to extend.
