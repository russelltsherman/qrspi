# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

> SCOPE NOTE — CRITICAL: The questions assume a merged "RUS-85 event-emitter" that
> writes `.qrspi/observability/events.jsonl`. **That module does not exist in this
> worktree.** `grep -rl "events.jsonl\|observability"` across `scripts/`, `.claude/`,
> and `docs/` returns only two *unrelated* comment hits (`qrspi_pr_state.py:345,627`
> and `qrspi-batch.js:2010`, all the English word "observability"), and there is no
> `.qrspi/observability/` directory, no `*events*.jsonl` file, and no `emit_event` /
> `event_type` writer anywhere. The only `*.jsonl` artifact actually produced is
> **`.qrspi/<id>/critic-metrics.jsonl`** (RUS-77/RUS-78), written by
> `scripts/qrspi_metrics_append.py`. Every RUS-85-targeted question (Q1, Q2, Q6, Q7,
> Q8) is therefore answered as **NOT FOUND for the RUS-85 artifact**, with the closest
> existing analogue (the critic-metrics ledger) documented as the precedent a tailer
> would build against. This is the most load-bearing finding in this document.

## Q1: What is the exact on-disk schema of each JSON line in `.qrspi/observability/events.jsonl` produced by RUS-85 — which fields are present (e.g. `ticket_id`, `phase`, `event_type`, `error_code`, `timestamp`) and what are their types and value ranges?

**Answer:** NOT FOUND for the RUS-85 `events.jsonl` artifact. No module writes
`.qrspi/observability/events.jsonl` in this worktree, and no `events.jsonl` file
exists on disk. Searches attempted: `grep -rln "event_type\|emit_event\|jsonl\|\.jsonl" scripts/ .claude/`,
`find . -name "*.jsonl"`, `grep -rl "events.jsonl\|observability"`. The only JSONL
producer is the **critic-metrics ledger**, the structural precedent a new event log
would mirror. Its line schema is the `CriticMetricsLedgerLine` envelope: a shallow
copy of a `CriticStepMetrics` record with three injected fields. The appender is the
sole envelope authority — its `ticketId`/`timestamp`/`runId` win over any pre-existing
values in the record.

**Evidence:**

```python
def wrap_envelope(record, ticket, timestamp, run_id):
    line = dict(record)
    line["ticketId"] = ticket          # str, e.g. "RUS-77"
    line["timestamp"] = timestamp      # str, UTC ISO-8601 (datetime.now(timezone.utc).isoformat())
    line["runId"] = run_id             # str, orchestrator per-invocation id
    return line
```

— `scripts/qrspi_metrics_append.py:67-79`

The inner `CriticStepMetrics` record is built by `build_record(verdicts, terminalAction, usage=None, phase=None)` at `scripts/qrspi_critic_metrics.py:54`. Each ledger line is one `json.dumps(ledger_line) + "\n"` (`scripts/qrspi_metrics_append.py:90`).
**Dependencies:** producer `qrspi_critic_metrics.build_record` → envelope authority `qrspi_metrics_append.wrap_envelope`/`append_line`; path resolution via `qrspi_paths.resolve_repo_root`.
**Implicit contracts:** one JSON object per line, newline-terminated; UTC ISO-8601 timestamp string; `ticketId`/`timestamp`/`runId` always present (injected, never trusted from the record). A tailer for a real event log should assume the same "envelope-injected provenance fields" convention rather than the RUS-85 field names in the question (`event_type`, `error_code`, `phase`), which are **unverified** — they appear only in the question, not in any code.

## Q2: How is the event log file currently rotated (size-based, time-based, or external) — what naming/path convention does a rotated file follow, so a tailer can detect rotation and reopen the new file?

**Answer:** NOT FOUND — there is **no rotation of any kind**. The only JSONL writer,
`qrspi_metrics_append.append_line`, opens the per-ticket ledger in append mode (`"a"`),
writes one line, and never truncates, renames, size-checks, or rolls the file. There is
no rotated-file naming convention to detect. Searches: `grep -rn "rotat\|getsize.*>\|rename\|RotatingFileHandler"` over scripts (no rotation logic; `os.path.getsize` is used only for a non-empty *verify*, not a size cap).

**Evidence:**

```python
def append_line(path, ledger_line):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(ledger_line) + "\n")
    try:
        size = os.path.getsize(path)   # used ONLY to fail-closed if empty, not to rotate
    except OSError:
        return 0, 0, "ledger not written: %s" % path
```

— `scripts/qrspi_metrics_append.py:82-94`

**Dependencies:** none — pure append to a per-ticket path.
**Implicit contracts:** the ledger is unbounded and append-only; one file per ticket (`.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`) rather than a single shared file. A tailer cannot rely on any existing rotation/reopen signal; rotation handling would be net-new. If a single shared `events.jsonl` is introduced, no precedent governs its naming.

## Q3: What pattern do existing `qrspi` subcommands follow for argument parsing, subcommand registration, and flag handling that a new `qrspi log query` command must conform to?

**Answer:** There is **no top-level `qrspi` CLI binary or subcommand dispatcher**. `find . -name qrspi` and `ls scripts/ | grep -i cli` return nothing; there is no `add_subparsers` anywhere. Every capability is a **standalone script** invoked as `python3 scripts/qrspi_<verb>.py` with its **own** `argparse.ArgumentParser` and **no** subcommands — flags only. A `qrspi log query` command would therefore be a *new* script `scripts/qrspi_log_query.py` (or similar) following the established single-script-per-tool idiom, not a subcommand added to an existing parser. The uniform conventions: stdlib-only `argparse`; `required=True` flags; self-location of the repo root from `__file__` or via `qrspi_paths.resolve_repo_root`; a single JSON envelope `{ok, ...}` printed to stdout; exit 0 on success / non-zero on failure; a pure unit-tested core with a thin `main(argv=None)` wrapper.

**Evidence:**

```python
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Append one critic-step metrics line to a per-ticket ledger "
                    "(self-locating)")
    parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-77")
    parser.add_argument("--record", required=True, help="...JSON string")
    parser.add_argument("--run-id", dest="run_id", required=True, help="...")
    args = parser.parse_args(argv)
```

— `scripts/qrspi_metrics_append.py:104-114` (representative; same shape at `scripts/qrspi_config.py:59-64`, `scripts/qrspi_comment_reply.py:30-55`)

**Dependencies:** scripts import sibling helpers via `sys.path.insert(0, ENGINE_ROOT)` where `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))` (`qrspi_metrics_append.py:52-55`).
**Implicit contracts:** `main(argv=None)` so tests pass an explicit arg list; stdout is machine-parseable JSON only (human progress is NOT printed by Python tools — it is the JS orchestrator's `log()`); exit code is the success signal; the `qrspi`-laden path token is *computed* by the script, never typed/required as a flag (the weak-worker mangling guard — see `qrspi_metrics_append.py:16-28`).

## Q4: How are config keys currently read and what is the supported key shape (flat top-level only, or nested dot-paths) — given existing keys like `ciReviseCap` are flat but this ticket specifies nested keys such as `observability.alerts.phaseTimeout`?

**Answer:** There are **two distinct config readers**, and nesting is supported only by a *purpose-built* resolver, never by the generic one:

1. `scripts/qrspi_config.py` — the **generic** reader. Reads **ONE flat top-level key only**; no dot-path support. `select_value(config, key, default)` does `config.get(key)` (`:36-42`); `read_config` returns the parsed dict or `{}` (`:45-56`). The JS side runs it as `python3 scripts/qrspi_config.py --key <name>` and parses via `parseConfigEnvelope`, which **rejects any non-string value** (`typeof env.value !== 'string'` ⇒ error) — so this reader cannot even surface a nested object.
2. `scripts/qrspi_critics_config.py` — a **dedicated, tested** resolver for the *nested* `critics.*` block. It reads `config.json` once and hand-walks the nested structure (`critics.design.maxRounds`, `critics.implementation.coherence.enabled`, etc.), emitting a fully-resolved per-phase envelope with config-value > default precedence.

So `ciReviseCap` is flat and read via `qrspi_resolve.load_ci_revise_cap` → `qrspi_config.read_config(...).get("ciReviseCap")` (`scripts/qrspi_resolve.py:406-412`, coerced by `coerce_cap` `:394-403`). A **nested** `observability.alerts.phaseTimeout` could NOT use the flat `qrspi_config.py`; it must follow the `qrspi_critics_config.py` precedent — a new dedicated resolver that reads `config.json` once and walks the nested block, returning a complete defaults-filled envelope. The example config already proves nested blocks are read this way (`critics` is a multi-level object).

**Evidence:**

```python
def select_value(config: dict, key: str, default: str) -> str:
    """Pure selector: return config[key] when present and truthy, else default."""
    value = config.get(key)
    return value if value else default
```

— `scripts/qrspi_config.py:36-42` (flat, single key)

```javascript
if (typeof env.value !== 'string') return { ok: false, error: `config: envelope value not a string (got ${env.value})` }
```

— `.claude/workflows/qrspi-batch.js:389` (`parseConfigEnvelope` rejects non-strings)

**Dependencies:** `qrspi_resolve.py` and the critics path both depend on `qrspi_config.read_config` for the raw dict load; nested resolution is layered on top in `qrspi_critics_config.py`.
**Implicit contracts:** generic config reads are flat-key/string-valued only; any nested key needs its own tested resolver that (a) reads config ONCE ("single read discipline"), (b) always returns a complete defaults-filled envelope so the JS consumer never special-cases a missing branch, and (c) treats a malformed/absent file as `{}` → all defaults (best-effort, never raises). See project memory "Config reader is single-top-level-key only" — this exact mismatch bit RUS-56.

## Q5: Where is the in-memory phase/ticket state for a run currently held, and is there an existing per-ticket state structure keyed by `ticket_id` that the new state store can extend or must coexist with?

**Answer:** Per-ticket "state" is **not held in a long-lived in-memory store**. It is (a) **derived on demand** by the pure resolver `scripts/qrspi_resolve_state.py` from a `state` dict the caller gathers per ticket, and (b) iterated transiently by the JS orchestrator `.claude/workflows/qrspi-batch.js`, which loops over tickets and calls the resolver per ticket. The resolver takes a single `state` object (entry-gate fields + per-phase branch/PR/CI state) and returns one decision; it performs **no I/O and holds no cross-ticket state** ("Keeping the decision pure makes it unit-testable"). There is no existing `Dict[ticket_id, State]` structure to extend — a new monitoring state store would be net-new and would coexist with (consume the events emitted alongside) this stateless-resolver design, not extend an in-memory structure.

**Evidence:**

```python
def resolve(state, ci_revise_cap=3):
    ...
```

— `scripts/qrspi_resolve_state.py:173`; header: "It performs NO I/O of its own — the caller ... gathers the state via gh/gt and feeds it in" (`:6-12`)

The orchestrator sweeps tickets and decides each independently (`.claude/workflows/qrspi-batch.js`, STATUSES sweep at `:170`).
**Dependencies:** `qrspi-batch.js` → `qrspi_resolve.py` (one-shot gather+decide) → `qrspi_resolve_state.resolve`.
**Implicit contracts:** state is keyed implicitly by ticket id at the *call boundary* (one resolve call per ticket); there is no persisted/in-memory accumulation across tickets or across runs. A monitoring store that needs cross-event accumulation (e.g. phase-start-without-end detection) cannot piggyback on the resolver and would maintain its own keyed-by-`ticketId` structure.

## Q6: What signals a ticket "completes" in the existing event stream (which `event_type`/`phase`/status value) so the state store knows when to reset per-ticket stores?

**Answer:** NOT FOUND in any event stream (no event stream exists — see scope note). Completion is expressed **only as a resolver decision and a Linear reporting status**, not an emitted event. The resolver returns `action="land"` when "All phases approved and clean" (`scripts/qrspi_resolve_state.py:373-374`) — this is the terminal autonomous action; landing the stack is what drives the ticket to `Done`. The Linear reporting projection is the status chain `Selected → Design Review → Plan Review → Code Review → Done` (`.claude/workflows/qrspi-batch.js:170` sweeps `['Selected','Design Review','Plan Review','Code Review']`; `Done` is the post-land terminal per `.claude/CLAUDE.md` lifecycle). The implementation phase is "complete" when every planned slice is committed AND `pr-summary.md` is committed (`qrspi_resolve_state.py:347-357`).

**Evidence:**

```python
    return decision("land", phase="implementation",
                    reason="All phases approved and clean; land the whole stack bottom-up.")
```

— `scripts/qrspi_resolve_state.py:373-374`

```javascript
const STATUSES = input?.statuses ?? ['Selected', 'Design Review', 'Plan Review', 'Code Review']
```

— `.claude/workflows/qrspi-batch.js:170`

**Dependencies:** resolver decision → orchestrator `doLand` → Linear status projection (best-effort).
**Implicit contracts:** "complete" is a *derived* condition (approved + clean + landed), not a discrete event with an `event_type`. A state store wanting a per-ticket reset signal has no existing completion *event* to subscribe to — it would have to infer completion from either a `land`-action event (if RUS-85 emits actions) or the `Done` status transition, both of which are **unverified** to be in any event stream.

## Q7: How does the current event-writing code behave on partial or truncated final lines (a line written but not yet flushed/newline-terminated) — what does the reader observe mid-write, which the tailer's JSON parsing must tolerate?

**Answer:** NOT FOUND for RUS-85. For the existing JSONL writer, the write is **atomic at the line granularity in intent**: `append_line` opens the file, writes `json.dumps(line) + "\n"` in a single `fh.write`, and closes via the `with` block (which flushes on exit). There is **no explicit `fh.flush()`/`os.fsync()`**, and the newline is part of the same write call, so a concurrent reader could in principle observe a partial line only during the write itself (the `with` exit guarantees flush before the function returns). No code reads this file back, so there is **no existing reader that tolerates partial lines** — that tolerance would be net-new for a tailer. There are no concurrent writers to a single shared file (each ticket has its own ledger).

**Evidence:**

```python
    with open(path, "a") as fh:
        fh.write(json.dumps(ledger_line) + "\n")   # data + newline in one write; flush on `with` exit
```

— `scripts/qrspi_metrics_append.py:89-90`

**Dependencies:** none (filesystem only).
**Implicit contracts:** writers append a complete `<json>\n` per invocation and rely on `with`-close to flush; there is no fsync durability guarantee and no append-locking. A tailer must defensively skip a trailing newline-less fragment (a line in-flight) and tolerate a final partial line on crash — no existing code does this, so it is a new requirement.

## Q8: What existing handling, if any, covers a phase that starts but never emits an end event (process crash/hang) — and how is "the file does not yet exist" vs "exists but empty" distinguished at startup before any event is written?

**Answer:** NOT FOUND — no existing code consumes an event log, so there is no start-without-end handling and no file-exists-vs-empty distinction at any consumer. The closest analogue: the *writer* `append_line` does `os.makedirs(dirname, exist_ok=True)` then opens in append mode (creating if absent), and uses `os.path.getsize` only to fail-closed if the file is empty *after* its own write (`qrspi_metrics_append.py:88-96`). Separately, `qrspi_resolve.py:420-434` (`worktree_is_healthy`) shows the codebase's idiom for distinguishing "looks present but is dead" — a path can pass `os.path.isdir()` yet be unusable — which is the conceptual precedent a tailer would follow (presence check is insufficient; probe content/liveness). Phase-timeout / start-without-end detection is entirely net-new.

**Evidence:**

```python
    if size == 0:
        return 0, 0, "ledger is empty after append: %s" % path
```

— `scripts/qrspi_metrics_append.py:95-96` (only existing "empty file" awareness — post-write, fail-closed)

**Dependencies:** none.
**Implicit contracts:** existing code treats "missing" and "creatable" identically on the *write* side (`makedirs ... exist_ok=True`, mode `"a"`). No consumer distinguishes missing vs empty at startup; a tailer must add: missing ⇒ wait/poll, exists-empty ⇒ open at offset 0, exists-nonempty ⇒ choose tail-from-start vs tail-from-end policy. Crash/hang detection has no precedent.

## Q9: What is the established unit-test convention for new pure-logic modules (e.g. the `scripts/*_test.py` stdlib-only siblings run by `scripts/run_tests.py`) that the tailer, state store, metrics calculator, and alert evaluators must follow?

**Answer:** The convention is firmly established. Each module `scripts/qrspi_<x>.py` has a **sibling** `scripts/qrspi_<x>_test.py` that is **stdlib-only `unittest`** (no pytest), runnable standalone as `python3 scripts/qrspi_<x>_test.py` (exit 0 pass / non-zero fail). Tests import the module by inserting the script dir on `sys.path` then importing the **pure functions** directly, exercising them with in-memory dicts and `tempfile.TemporaryDirectory()` — **never touching the real repo**. The aggregating runner `scripts/run_tests.py` discovers every `*_test.py` (`discover_tests`, `:36-48`), runs each as its own subprocess with a 180s timeout (`run_one`, `:51-75`), and exits non-zero if any fails (`:137-138`). The same command is the CI regression gate (`.github/workflows/tests.yml`).

**Evidence:**

```python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qrspi_config import read_config, select_value  # noqa: E402

class SelectValueTests(unittest.TestCase):
    def test_key_present_and_truthy_returns_value(self):
        self.assertEqual(select_value({"linearProject": "Acme"}, "linearProject", "QRSPI"), "Acme")
```

— `scripts/qrspi_config_test.py:15-25`; runner discovery at `scripts/run_tests.py:36-48`

**Dependencies:** `run_tests.py` (and CI) depend on the `*_test.py` naming suffix and on each test being a self-contained subprocess.
**Implicit contracts:** (1) keep a pure, argument-driven core separate from `main()` so it is testable without I/O; (2) name the test file `<module>_test.py` so the runner discovers it; (3) stdlib only; (4) standalone-runnable with `unittest.main()`/exit code; (5) never read the real `.qrspi/config.json` — use tempdirs/in-memory dicts; (6) `main(argv=None)` so tests can drive the CLI wrapper too. The tailer/state-store/metrics-calculator/alert-evaluator each need a pure core + a `*_test.py` sibling to be picked up by CI.

## Q10: How are end-to-end / integration scenarios currently exercised given the `evals/` harness is a non-functional placeholder — what mechanism would let an integration test feed RUS-85-emitted events and assert alerting fires?

**Answer:** `scripts/run_eval.py` is a **non-functional placeholder** (confirmed: `ExecutionResult.executed` defaults `False`; its docstring describes intent only; project memory + `.claude/CLAUDE.md` both label `evals/` + `run_eval.py` non-functional). There is **no functional end-to-end harness**. The only real verification mechanisms are (1) the **stdlib unit tests** via `run_tests.py`, and (2) **manual end-to-end runs** ("verify pure logic with the unit tests and orchestration changes with manual end-to-end runs", `.claude/CLAUDE.md`). The practical mechanism to "feed events and assert alerting fires" is therefore a **fixture-driven unit/integration test**: write synthetic JSONL event fixtures to a `tempfile.TemporaryDirectory()` and call the tailer/evaluator's pure core against them, asserting on the returned alert payloads — exactly the `tempfile`-based pattern in the existing `*_test.py` siblings (e.g. `qrspi_config_test.py`'s `ReadConfigTests` writes a config to a tmp dir and reads it back). Fixtures already live under `scripts/fixtures/` (used by contract-fixture tests).

**Evidence:**

```python
@dataclass
class ExecutionResult:
    ...
    executed: bool = False
```

— `scripts/run_eval.py:19-29` (placeholder; nothing flips `executed`)

```python
def test_present_file_parses(self):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        self._write_config(root, json.dumps({"linearProject": "Acme"}))
        self.assertEqual(read_config(root), {"linearProject": "Acme"})
```

— `scripts/qrspi_config_test.py:52-56` (the real fixture-driven pattern to reuse)

**Dependencies:** `run_tests.py` is the only live gate; `scripts/fixtures/` holds shared test fixtures (e.g. `qrspi_contract_fixtures_*_test.py`).
**Implicit contracts:** integration coverage = pure core + tempdir/fixture JSONL inputs asserted via `unittest`; do NOT build on `run_eval.py`/`evals/`. A real e2e through the orchestrator is manual only.

## Q11: What is the existing CLI logging mechanism and how are log levels (`warn`, `error`) emitted, so alerts can be written at the correct level in machine-parseable JSON?

**Answer:** There is **no leveled logging facility** and **no `logging`-module usage** anywhere in `scripts/` (`grep "import logging"` → none). Two separate output disciplines exist:

1. **Python tools** never print human logs — they print a **single JSON envelope** to **stdout** carrying `ok: bool` and, on failure, an `error: <verbatim string>` field; the **exit code** is the success signal. There is no `warn`/`error` *level* — severity is encoded as `ok:false` + `error`. (`qrspi_config.py:71-74`, `qrspi_metrics_append.py:137-149`, `qrspi_critics_config.py:261-264`.) `qrspi_critics_config.py` additionally carries a `warnings: [str]` array in its envelope for non-fatal notices (`:261`).
2. **The JS orchestrator** emits human-readable progress via a `log(...)` function (used pervasively, e.g. `qrspi-batch.js:766,813,837,844`). `log` is an **injected harness global** — it is not defined in the file (`grep -E "(const|let|function|var) +log"` → no definition), consistent with the file being harness-coupled (top-level `return`, injected globals — see `.claude/CLAUDE.md`).

So "alerts at the correct level in machine-parseable JSON" has no existing leveled precedent. The closest machine-parseable convention is the `{ok, ..., warnings?, error?}` stdout envelope; a `level` field (`warn`/`error`) on an alert payload would be **net-new**, though it fits the existing JSON-to-stdout discipline.

**Evidence:**

```python
print(json.dumps({"ok": False, "key": key, "value": None, "error": str(exc)}))
```

— `scripts/qrspi_config.py:74`

```python
print(json.dumps({"ok": True, "phases": phases, "warnings": warnings}))
```

— `scripts/qrspi_critics_config.py:261` (the only `warnings`-array precedent)

**Dependencies:** JS `parseConfigEnvelope`/`parseCriticsEnvelope` consume these stdout envelopes; `parseCriticsEnvelope` forwards each `warnings` entry to the injected `log()` (`qrspi-batch.js:410`).
**Implicit contracts:** machine output = one JSON object on stdout; severity today is binary (`ok` + optional `error`) plus an optional `warnings` string array — there is no `warn`/`error`/`info` level enum to conform to; human progress is the JS `log()` global, off-limits to Python tools.

## Q12: Are there existing alert-formatting or metrics/histogram utilities in the codebase that the percentile (p50/p90/p95/p99) computation and JSON alert payloads can reuse rather than reimplement?

**Answer:** NOT FOUND — no percentile, histogram, quantile, or alert-formatting utility exists. `grep -rln "percentile\|histogram\|p50\|p90\|p95\|p99\|quantile" scripts/ .claude/` returns only `scripts/qrspi_teeth_test.py:101-102`, where the strings `"p95"`/`"200ms"` are **test fixture keyword tokens** (a string-matching test about latency-related ticket text), **not** a percentile implementation. The only metrics-adjacent code is the critic-metrics family — `qrspi_critic_metrics.build_record` (`:54`, builds a per-step record), `qrspi_metrics_append` (appends ledger lines), and `qrspi_critic_summary.py` (rolls up critic metrics, prints a JSON summary at `:204`) — but none compute percentiles or format alerts. Percentile math (p50/p90/p95/p99) and JSON alert payloads would be **net-new** and should be implemented as a pure, unit-tested module per the Q9 convention (Python stdlib has no percentile helper besides `statistics.quantiles`, available 3.8+).

**Evidence:**

```python
    if "p95" in low or "200ms" in low or "latency" in low:
        tokens.update({"p95", "perf/", "load-test"})
```

— `scripts/qrspi_teeth_test.py:101-102` (string-token test fixture; NOT a percentile util)

`qrspi_critic_summary.py` rolls up metrics but only prints a summary dict: `print(json.dumps(summary))` (`:204`) — no percentiles.
**Dependencies:** critic-metrics chain: `build_record` → `qrspi_metrics_append` → `qrspi_critic_summary`.
**Implicit contracts:** metrics summarization today is a flat roll-up printed as a JSON dict; there is no statistical/percentile layer and no alert-payload formatter to reuse. New percentile/alert code must be a fresh pure module with a `*_test.py` sibling.

---

## Discovered Patterns

- **Standalone-script-per-tool, no umbrella CLI.** Every capability is `python3 scripts/qrspi_<verb>.py` with its own `argparse` and flags; there is no `add_subparsers` and no `qrspi` dispatcher binary. A "`qrspi log query` subcommand" must be reconciled with this reality (likely a new standalone script).
- **Functional-core / imperative-shell split.** Python = pure, unit-tested logic (resolvers, reducers, selectors) with thin `main(argv=None)` wrappers; `qrspi-batch.js` = harness-coupled imperative orchestration (injected globals like `log`, top-level `return`, not unit-testable). New monitoring logic should land on the Python (tested) side. (project memory: "Testing dynamic workflow scripts".)
- **Self-locating, fail-closed I/O helpers.** Write/append helpers (`qrspi_persist.py`, `qrspi_metrics_append.py`, `qrspi_comment_reply.py`, `qrspi_pr_body.py`) all resolve the repo root via `qrspi_paths.resolve_repo_root` (git-common-dir first, `validate=False` to keep `gh` off the import path), verify the write is non-empty, and fail closed. The `qrspi` path token is *computed by the script*, never typed by a worker.
- **Single JSON envelope on stdout = the machine interface.** `{ok: bool, ...}` with optional `error`/`warnings`; exit code mirrors `ok`. JS parses with `extractJsonObject` + a typed `parse*Envelope` validator.
- **"Single read discipline" for config.** Read `config.json` once into a tested resolver that returns a complete defaults-filled envelope (`qrspi_critics_config.py`); the generic `qrspi_config.py` is flat-key/string-only by design.
- **Per-ticket artifact paths, not shared files.** The one existing JSONL ledger is per-ticket (`.qrspi/<id>/critic-metrics.jsonl`), append-only, unbounded, unrotated.
- **`@me` / config-driven indirection** for shareability — nothing user/team-specific is hard-coded; sourced from gitignored `.qrspi/config.json` with documented defaults in `.qrspi/config.example.json`.

## Inconsistencies

- **Questions assume a merged RUS-85 event-emitter that is absent from this worktree.** Q1, Q2, Q6, Q7, Q8 (and parts of Q10/Q11) target `.qrspi/observability/events.jsonl` and field names (`event_type`, `error_code`, `phase`) that exist nowhere in the code — no writer, no file, no directory. Either RUS-85 is unmerged/on another branch (this worktree is on `main` and its git worktree metadata is currently detached — `git` commands failed with "not a git repository: .../worktrees/RUS-87", so branch state could not be confirmed via git), or the event-log field schema in the questions is *speculative*. The only real JSONL precedent is the critic-metrics ledger, whose provenance fields are `ticketId`/`timestamp`/`runId`, NOT the question's `ticket_id`/`event_type`/`error_code`.
- **Field-naming casing mismatch.** Existing JSONL uses **camelCase** (`ticketId`, `runId`); the questions use **snake_case** (`ticket_id`, `event_type`). If a new event log is meant to align with existing ledgers, the questions' snake_case is inconsistent with the codebase convention.
- **`qrspi_config.py` docstring vs reality on nesting.** The flat reader's docstring/output implies generic config access, but it (and the JS `parseConfigEnvelope`) silently cannot represent nested values — a non-string value is rejected as an error. The nested `critics` block works *only* because a separate resolver (`qrspi_critics_config.py`) exists. A ticket specifying nested `observability.*` keys that assumes "an existing config path" would be wrong (this exact gap bit RUS-56; see project memory "Config reader is single-top-level-key only").
- **`run_eval.py` docstring describes a working harness it is not.** Its module docstring ("Runs each test case multiple trials in isolated environments, capturing full transcripts...") describes behavior the placeholder does not perform (`executed` is never set true); `.claude/CLAUDE.md` and project memory both correctly flag it non-functional. Treat the docstring as aspirational, not factual.
