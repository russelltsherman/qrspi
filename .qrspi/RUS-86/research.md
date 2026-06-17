# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-17T00:00:00Z
**Generated:** 2026-06-17T00:00:00Z
**Status:** draft

All paths below are relative to the worktree root `/workspaces/qrspi/.worktrees/RUS-86`.

## Q1: At which points in the phase lifecycle does the pipeline currently mark phase start, end, success, failure, and retry, and what call sites would an event emitter hook into to emit a JSONL event at each transition?

**Answer:** There is **no structured event emission today** — phase transitions are marked only by free-text `log(...)` calls (an injected harness global; not defined in the file) and by the boolean return of `runPhase`. The natural hook points are all inside `runPhase` (`.claude/workflows/qrspi-batch.js:1290`):
- **phase_start:** at the top of `runPhase`, right after the `existing[name]` reuse short-circuit (`:1291-1294` returns early "reusing existing").
- **phase agent spawned:** `const res = await agent(...)` at `:1295`.
- **phase_failure (agent):** `res === null` branch at `:1296-1299`.
- **node-check / critic-loop failure:** `:1321-1328`, `:1335-1350` (each returns `false`).
- **phase_success / phase_end:** after `persistArtifact` succeeds at `:1354-1360` (`return true`); the persist failure path `:1355-1357` is the real failure gate.

The action-level transitions (run_design / advance / submit / land / revise / reset) are dispatched in the per-ticket loop near `:2700-2710`, where each ticket's `res.action` is logged. `qrspi_resolve_state.py`/`qrspi_resolve.py` **decide** actions but emit no events; they return a JSON envelope.

**Evidence:**

```js
async function runPhase(name, agentType, prompt, existing, id, phaseLabel, criticConfig) {
  if (existing && existing[name]) {
    log(`  ${id}: reusing existing ${name}.md`)
    return true
  }
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
  if (res === null) {
    log(`  ${id}: ${name} phase failed or was skipped — stopping this ticket`)
    return false
  }
  ...
  const p = await persistArtifact(id, name, phaseLabel)
  if (!p || !p.ok) { ...; return false }
  log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
  return true
}
```

— `.claude/workflows/qrspi-batch.js:1290-1361`
**Dependencies:** `runPhase` → `agent()` (harness global), `persistArtifact()` → `scripts/qrspi_persist.py`. Callers: `doDesign`/`doPlan`/`doImplementation` (the action dispatchers).
**Implicit contracts:** `runPhase` returns a plain boolean; a phase is "successful" iff `persistArtifact` moved a non-empty staged file. `log()` is an injected global — any emitter added in JS must tolerate it being a no-op in the sandbox. Persist is the single success gate; an event emitter must fire success only after `p.ok`.

## Q2: How does data flow from a phase agent through persistence today (the staging + deterministic move in `qrspi_persist.py`), and where would phase_start / phase_end / phase_success / phase_failure events naturally be emitted?

**Answer:** Fix A flow: the phase **agent writes its artifact to a token-free staging path** `stg(id, name)` = `/tmp/phase-stage/<id>/<name>.md` (`.claude/workflows/qrspi-batch.js:633`). `runPhase` then calls `persistArtifact` (`:656+`) which shells out to `scripts/qrspi_persist.py --ticket <id> --artifact <name>`. The script self-locates the host root via `qrspi_paths.resolve_repo_root(validate=False)`, computes the canonical dest `<root>/.worktrees/<id>/.qrspi/<id>/<name>.md` (`dest_path`, `qrspi_persist.py:67-71`), verifies the staged file is non-empty, `shutil.move`s it, re-verifies non-empty, and prints `{ok, repoRoot, src, dest, bytes, error?}`. Natural event hooks: **phase_start** before `agent()`; **phase_success/phase_end** after `p.ok` in `runPhase`; **phase_failure** on the `res===null` / `!p.ok` branches. Emitting inside `qrspi_persist.py` itself would only capture success/failure of the move, not start.

**Evidence:**

```python
def persist(src, dest):
    try:
        size = os.path.getsize(src)
    except OSError:
        return 0, "staged artifact not found or unreadable: %s" % src
    if size == 0:
        return 0, "staged artifact is empty: %s" % src
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(src, dest)
    ...
    return out, None
```

— `scripts/qrspi_persist.py:74-92`
**Dependencies:** `qrspi_persist.py` imports `qrspi_paths` (sibling, via `sys.path.insert(0, ENGINE_ROOT)` at `:45-48`). Consumed by `persistArtifact` in the JS orchestrator.
**Implicit contracts:** STAGE_ROOT `/tmp/phase-stage` is duplicated in two places that must stay in sync — `qrspi_persist.py:57` and the JS `stg()` at `:633` (the script's docstring at `:54-57` notes this). The envelope is single-line-ish JSON on stdout, parsed by JS; any new emitter must not pollute stdout of these scripts.

## Q3: How are `trace_id` / `span_id` / `parent_span_id` propagated across a ticket's lifetime and nested operations, and what carries ticket context between the JS orchestrator and the Python scripts?

**Answer:** **No trace/span concept exists today.** The closest existing primitive is `runId` (`.claude/workflows/qrspi-batch.js:118-126`): a per-invocation id computed ONCE from `process.env.QRSPI_RUN_ID` else `crypto.randomUUID()` else a `crypto.getRandomValues` hex fallback else the constant `'run-fallback'`. It is the only cross-cutting correlation id and is currently passed only to the metrics appender. Ticket context flows JS→Python **purely as explicit CLI flags** — every script takes `--ticket <id>` (and the resolver also `--run-id`); there is no shared context object, env-carried trace, or parent/child span linkage. Nested operations (phase → critic round → lens) are not correlated by any id beyond `runId` + `ticketId` + `phase` on the metrics ledger line.

**Evidence:**

```js
const runId =
  (typeof process !== 'undefined' && process.env && process.env.QRSPI_RUN_ID) ||
  (typeof crypto !== 'undefined' && crypto.randomUUID && crypto.randomUUID()) ||
  ( ... crypto.getRandomValues ... `run-${hex}`) ||
  'run-fallback'
```

— `.claude/workflows/qrspi-batch.js:118-126`

```js
... python3 ${engineCmd('scripts/qrspi_metrics_append.py')} --ticket ${id} --run-id '${runId}' --record "$(cat ...)" ...
```

— `.claude/workflows/qrspi-batch.js:980`
**Dependencies:** `runId` → `qrspi_metrics_append.py` (`--run-id`, stamped as `runId` on every ledger line, `qrspi_metrics_append.py:67-79`).
**Implicit contracts:** `runId` is "always present, always a string" (comment at `:113`). Workflow scripts **forbid `Date.now()`/`Math.random()`** (they break resume — `:115-117`); any trace/span id generation MUST use `crypto`, not timestamps. Ticket context is conveyed strictly by `--ticket` flags, never env vars or a context file (except the resolver's `ticketContentPath` for the design body).

## Q4: What is the existing signature and invocation convention for the self-locating Python scripts, so a new event-emitter module follows the same repo-root self-location and CLI contract?

**Answer:** Convention is uniform across `qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_metrics_append.py`, `qrspi_config.py`:
1. Shebang `#!/usr/bin/env python3`, module docstring with a "Why this exists" + "Output: a single JSON envelope on stdout" block.
2. `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))` + `sys.path.insert(0, ENGINE_ROOT)` for sibling imports (`qrspi_persist.py:45-48`).
3. **Host root** resolved via `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` — git-common-dir first so it is the MAIN checkout even from a worktree (`qrspi_persist.py:50`, `qrspi_metrics_append.py:131`). (`qrspi_config.py` is the exception: it uses `Path(__file__).resolve().parents[1]`, `:29`.)
4. `argparse` with short token flags (`--ticket`, `--artifact`, `--run-id`, `--key`), `choices=ARTIFACTS` where applicable.
5. Pure helpers separated from I/O (unit-tested), subprocess mechanics segregated.
6. Print one JSON envelope `{ok: bool, ..., error?}` to stdout; `return 0 if ok else 1`. Fail-closed, report once, never retry.

**Evidence:**

```python
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)
import qrspi_paths  # noqa: E402
REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)
```

— `scripts/qrspi_persist.py:45-50`
**Dependencies:** all four import `qrspi_paths`; `qrspi_resolve.py` additionally imports `qrspi_pr_state`, `qrspi_resolve_state`, `qrspi_config`.
**Implicit contracts:** A new emitter module should: self-locate the host root via `qrspi_paths.resolve_repo_root(validate=False)`, take `--ticket`/`--phase`/etc. as flags, print a JSON envelope on stdout, exit non-zero on error, keep a pure I/O-free core for `_test.py` coverage, and **keep stdout clean** (callers parse it). Use `crypto`-free / timestamp-allowed in Python (the no-`Date.now()` rule is a JS-workflow constraint only; Python freely uses `datetime.now(timezone.utc).isoformat()`, see `qrspi_metrics_append.py:133`).

## Q5: How does the codebase read configuration today (single-top-level-key constraint), and how would nested `observability.*` keys be read?

**Answer:** Two readers exist, both **single-top-level-key only**:
- **Python:** `qrspi_config.read_config(repo_root)` parses `<root>/.qrspi/config.json` → dict (`{}` on any error, never raises, `qrspi_config.py:45-56`); `select_value(config, key, default)` returns `config[key]` if truthy else a per-key default (`:36-42`). The CLI `--key` resolves exactly **one top-level key** (`main`, `:59-75`). There is **no dot-path support**. `qrspi_resolve.py:405-411` (`load_ci_revise_cap`) calls `qrspi_config.read_config(...).get("ciReviseCap")` — i.e. it reads a nested-free flat key directly off the parsed dict.
- **JS:** `parseConfigEnvelope(text, key)` validates the worker's echo of `qrspi_config.py --key`'s output and **rejects a non-string `value`** (`:374`) — so the JS path can only consume flat string values.

**For nested `observability.*`:** the JS `--key`/`parseConfigEnvelope` path cannot carry nested objects (non-string value → ok:false). The viable pattern is the one `load_ci_revise_cap` already uses for `ciReviseCap`: a **Python-side reader that calls `qrspi_config.read_config()` and reaches into the parsed dict itself** (`config.get("observability", {}).get("eventLog")`), with its own coercion helper (mirroring `coerce_cap`, `:393-402`). The critic config (`qrspi_critics_config.py`, referenced in config.example.json `:6`) is the existing precedent for reading a **nested config block** via a dedicated tested resolver that prints a richer envelope — see Q6/Discovered Patterns.

**Evidence:**

```python
def load_ci_revise_cap(repo_root=REPO_ROOT):
    config = qrspi_config.read_config(repo_root)
    return coerce_cap(config.get("ciReviseCap"))
```

— `scripts/qrspi_resolve.py:405-411`

```js
if (typeof env.value !== 'string') return { ok: false, error: `config: envelope value not a string (got ${env.value})` }
```

— `.claude/workflows/qrspi-batch.js:374`
**Dependencies:** `qrspi_config.read_config` is the shared low-level parser; `qrspi_resolve.load_ci_revise_cap` and `qrspi_critics_config.py` both build on it.
**Implicit contracts:** `read_config` is best-effort and never raises (`{}` on OSError/ValueError). The `--key` CLI + JS envelope path is for **flat string** values only. Nested blocks must be read by a dedicated Python resolver that returns its own typed envelope — do NOT extend the `--key` path. Project memory confirms: "Config reader is single-top-level-key only".

## Q6: What does `.qrspi/config.json` / `config.example.json` look like, and are nested objects already present that an `observability` block would parallel?

**Answer:** `.qrspi/config.json` does NOT exist in the worktree (it is gitignored). `.qrspi/config.example.json` (40 lines) is the template. It **already contains nested objects**: `critics` (with sub-blocks `critics.design` carrying `candidates`/`digest.enabled`/`enabled`/`lenses`/`maxRounds`, and `critics.implementation.coherence.enabled`/`maxRounds`). Flat top-level keys: `ciReviseCap` (int, default 3), `linearProject`, `linearTeam`, `reviewers` (array), `teamReviewers` (array). Every block carries a `$comment*` documentation key the harness ignores. So an `observability` block would directly parallel the existing nested `critics` block — and `critics` is read by a dedicated resolver `scripts/qrspi_critics_config.py` (the "tested resolver" / "single read discipline"), exactly the pattern an `observability` resolver would follow.

**Evidence:**

```json
"critics": {
    "$comment": "... resolved by scripts/qrspi_critics_config.py (the tested resolver) ...",
    "design": { "candidates": 1, "digest": { "enabled": false }, "enabled": false,
                "lenses": [...], "maxRounds": 2 },
    "implementation": { "coherence": { "enabled": false, "maxRounds": 2 } }
},
"ciReviseCap": 3,
"linearProject": "QRSPI",
```

— `.qrspi/config.example.json:6-34`
**Dependencies:** `critics` block ↔ `scripts/qrspi_critics_config.py` (resolver) ↔ JS `parseCriticsEnvelope` (`.claude/workflows/qrspi-batch.js:388-397`, falls back to `DEFAULT_CRITIC_PHASES` on any garble).
**Implicit contracts:** Nested blocks default OFF / take per-block defaults when omitted; every key gets a sibling `$comment`. A resolver prints `{ok, phases/value, warnings}` and the JS side falls back to in-code defaults on any parse failure (never gates the run on bad config).

## Q7: Where is the exponential-backoff retry policy "already defined in the pipeline config" that the retry events must follow?

**Answer:** **NOT FOUND in the QRSPI pipeline.** There is no exponential-backoff retry policy in `.qrspi/config.json`/`config.example.json`, in the resolver, the batch orchestrator, or any `qrspi_*` script. The QRSPI pipeline's explicit posture is the **opposite** of retry-with-backoff: scripts "report ONCE as ok:false ... never retried" (`qrspi_persist.py:24-25`, `qrspi_resolve.py:20-21`) and worker prompts repeatedly say "HARD STOP, do NOT retry" (e.g. `.claude/workflows/qrspi-batch.js:670,693,892`).

The ONLY exponential-backoff in the repo is in the **eval-harness judge**, unrelated to the phase pipeline: `scripts/grade.py:653` `JUDGE_BACKOFF_BASE = 1.0  # seconds; doubled each retry`, `JUDGE_MAX_ATTEMPTS = 3` (`:652`), applied in a bounded-retry helper at `:866-881` (`time.sleep(JUDGE_BACKOFF_BASE * (2 ** attempt))`). Note `evals/`/`grade.py` is documented as a non-functional placeholder (CLAUDE.md). The closest pipeline "retry" semantics is the **CI-revise cap** (`ciReviseCap`, default 3) — a consecutive-red-CI counter, not a timed backoff (see Q8).

Searches attempted: `grep -rni "backoff|exponential|retry_polic|attempt_count|max_retries|retries"` over `.qrspi/`, `scripts/`, `docs/`.

**Evidence:**

```python
JUDGE_MAX_ATTEMPTS = 3
JUDGE_BACKOFF_BASE = 1.0  # seconds; doubled each retry
```

— `scripts/grade.py:652-653`
**Dependencies:** `grade.py` backoff is internal to the eval judge client; nothing in the phase pipeline depends on it.
**Implicit contracts:** If retry/backoff events are required by the ticket, the policy they must follow **does not exist yet** and would need to be introduced (likely as a new `observability`-adjacent or pipeline config block). The CI-revise cap (Q8) is the only existing bounded-retry mechanism and exposes an integer count, not backoff seconds.

## Q8: How is the `CI-Revise-Attempt: N` head-commit trailer counter maintained today, and must a `retry_attempt`/`retry_count` event field stay consistent with it?

**Answer:** The counter is a **head-commit message trailer** `CI-Revise-Attempt: N`, the durable observable-from-GitHub consecutive-red counter (RUS-81/RUS-83). Maintenance is split:
- **Read (gather):** `qrspi_pr_state.ci_revise_attempt(message)` parses the trailer via regex `^CI-Revise-Attempt:\s*(\d+)\s*$` (MULTILINE); absent/malformed → 0; last occurrence wins (`scripts/qrspi_pr_state.py:112-130`). The gather attaches it as `ciReviseAttempt` and **forces it to 0 whenever `ciState != "red"`** (read-side reset; `:296-320`).
- **Write (orchestrator-owned, RUS-83):** the worker NEVER writes it. After the revise worker returns, `doRevise` advances/resets it: CI path → `bumpCiReviseTrailers` → `scripts/qrspi_ci_revise_bump.py` (deterministic +1 per still-red branch, pure core `bump_ci_revise_trailer`, `qrspi_ci_revise_bump.py:91-100`); non-CI amend → `resetCiReviseTrailer` overwrites to 0 (`.claude/workflows/qrspi-batch.js:2155-2199`).
- **Resolve:** when the effective count reaches `ciReviseCap` (default 3), the resolver flips red→`wait` with `ciGaveUp`.

A new `retry_attempt`/`retry_count` event field **should source from this same trailer value** (the single shared serialization contract — `qrspi_ci_revise_bump.py:26-30` calls it "the shared serialization contract between writer and reader") to avoid a divergent second counter. It is a CI-revise count, not a generic phase-retry count.

**Evidence:**

```python
_CI_REVISE_ATTEMPT_RE = re.compile(r"^CI-Revise-Attempt:\s*(\d+)\s*$", re.MULTILINE)

def ci_revise_attempt(message):
    matches = _CI_REVISE_ATTEMPT_RE.findall(message or "")
    if not matches:
        return 0
    try:
        return int(matches[-1])
    except (TypeError, ValueError):
        return 0
```

— `scripts/qrspi_pr_state.py:112-130`
**Dependencies:** `qrspi_pr_state.ci_revise_attempt` (read) ↔ `qrspi_ci_revise_bump.bump_ci_revise_trailer` (write) share the trailer regex/semantics. `doRevise` (`.claude/workflows/qrspi-batch.js:1952+`) orchestrates both; the resolver consumes the count for the cap.
**Implicit contracts:** The trailer is the SINGLE serialization contract: absent ⇒ 0, last-occurrence wins, exactly one line written. Two resets (read-side in gather when not-red; writer-side on every non-CI amend). The orchestrator owns the writes; an event emitter must READ the count, never write the trailer.

## Q9: What is the current append/flush behavior for files the pipeline writes, and is there an existing single-line, flush-before-continue / crash-safe write pattern the JSONL append must match?

**Answer:** The directly-relevant precedent is **`qrspi_metrics_append.py` — the existing JSONL appender**. `append_line(path, ledger_line)` does `os.makedirs(parent, exist_ok=True)`, then `open(path, "a")` and `fh.write(json.dumps(ledger_line) + "\n")` inside a `with` (the context-manager close flushes), then **re-verifies the file is non-empty** and counts lines (`qrspi_metrics_append.py:82-99`). This is the JSONL-append + non-empty-verify + fail-closed pattern. It does **not** use `fsync`, `flock`, or atomic rename — it relies on `O_APPEND` (mode `"a"`) + close-flush. The other write patterns: `qrspi_persist.py` uses `shutil.move` (rename-style, single-file artifact), and `scripts/qrspi_clear_stale_pr.py:120` is the ONLY atomic-rename-on-write in the repo (`os.replace(tmp, path)  # atomic: never leave a half-written cache`) — but that is for a full-file cache, not an append. There is no explicit `fh.flush()`/`os.fsync()` anywhere in the pipeline writers.

**Evidence:**

```python
def append_line(path, ledger_line):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(ledger_line) + "\n")
    try:
        size = os.path.getsize(path)
    except OSError:
        return 0, 0, "ledger not written: %s" % path
    if size == 0:
        return 0, 0, "ledger is empty after append: %s" % path
    with open(path) as fh:
        lines = sum(1 for _ in fh)
    return lines, size, None
```

— `scripts/qrspi_metrics_append.py:82-99`
**Dependencies:** `qrspi_metrics_append.append_line` is the closest existing JSONL-append; `qrspi_clear_stale_pr.py` is the atomic-rename precedent for whole-file writes.
**Implicit contracts:** Each appended line is exactly one `json.dumps(...) + "\n"` (single-line JSONL). Fail-closed: a write that leaves the file empty returns an error. No `fsync`/locking exists — a crash-safe JSONL append must match the `O_APPEND` + close-flush + non-empty-verify pattern (and would have to ADD fsync if stronger durability is required, since none exists today).

## Q10: How does the codebase handle a missing or unwritable `.qrspi/observability/` directory (and `archive/`), and is there a directory-creation convention the rotation/archival path must follow?

**Answer:** The universal convention is **`os.makedirs(os.path.dirname(dest), exist_ok=True)` immediately before writing** — used in `qrspi_persist.persist` (`:84`) and `qrspi_metrics_append.append_line` (`:88`). There is no pre-flight check for an unwritable directory; an unwritable target surfaces as the `OSError`/exception caught by the script's outer try and reported as `ok:false`. No `.qrspi/observability/` or `archive/` directory exists today. The existing `.qrspi/<id>/` artifact dirs and the `critic-metrics.jsonl` ledger dir are created lazily this way. For nested subdirs (e.g. `observability/archive/`), `os.makedirs(..., exist_ok=True)` already creates intermediate dirs, so the same one-liner suffices.

**Evidence:**

```python
os.makedirs(os.path.dirname(dest), exist_ok=True)
shutil.move(src, dest)
```

— `scripts/qrspi_persist.py:84-85`
**Dependencies:** all artifact/ledger writers call `os.makedirs(..., exist_ok=True)` against a path computed off `resolve_repo_root`.
**Implicit contracts:** Directories are created lazily at write time, never provisioned ahead; `exist_ok=True` makes it idempotent. An unwritable path is NOT pre-checked — it fails at the write and is reported as `ok:false` (fail-closed, report once). A rotation/archival path should `os.makedirs(archive_dir, exist_ok=True)` then write, mirroring this.

## Q11: When the event log hits the rotation threshold mid-run while events are still appended, what existing locking or concurrency guard protects shared files, given multiple agents run concurrently across worktrees?

**Answer:** **NO file locking or concurrency guard exists anywhere in the pipeline.** Searches for `flock`, `fcntl`, `lockf`, `threading.Lock`, `filelock`, `O_EXCL`, `tempfile.mkstemp` returned nothing in the `qrspi_*` scripts. The only "atomicity" primitive is the single `os.replace(tmp, path)` in `scripts/qrspi_clear_stale_pr.py:120` (atomic rename of a whole-file cache — prevents a half-written file, not concurrent-writer races). Concurrency is instead avoided **by isolation**: each ticket runs in its own worktree `.worktrees/<id>/`, and per-ticket artifacts (including `critic-metrics.jsonl`) are written under that ticket's `.qrspi/<id>/` dir — so two agents never write the same file. Per-ticket ledgers sidestep cross-worktree contention entirely. A **shared/global** event log (not per-ticket) would be a NEW concurrency surface with no existing guard to reuse.

Searches attempted: `grep -rn "flock|fcntl|lockf|threading.Lock|filelock|O_EXCL|tempfile.mkstemp|os.replace|fsync|os.O_APPEND" scripts/*.py`.

**Evidence:**

```python
os.replace(tmp, path)  # atomic: never leave a half-written cache
```

— `scripts/qrspi_clear_stale_pr.py:120` (the only atomicity primitive; whole-file, not append/lock)
**Dependencies:** isolation is structural — `qrspi_metrics_append.ledger_path` writes to `<root>/.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl` (`qrspi_metrics_append.py:60-64`), one ledger per ticket.
**Implicit contracts:** Concurrency safety today = **per-ticket worktree isolation**, NOT locking. A per-ticket event log inherits that isolation for free. Any cross-worktree shared log would need a NEW guard (none exists to reuse), or must be partitioned per-ticket to stay safe. Rotation mid-append on a single-writer per-ticket file is safe under append + atomic-rename of the rotated-out file.

## Q12: How are unknown/malformed `event_type` / `phase` / `status` values rejected elsewhere, and is there a JSON-schema validation pattern the event schema would plug into?

**Answer:** Validation is done by **stdlib `argparse` `choices=[...]` and small hand-rolled checks**, NOT JSON-Schema in Python. Examples: `qrspi_persist.py:101-102` `--artifact ... choices=ARTIFACTS` (the 6-artifact whitelist `:52`); `qrspi_resolve.py:59` `ARTIFACTS` list; the resolver's `RESOLVE_ACTIONS` set in JS (`.claude/workflows/qrspi-batch.js:216-218`). Free-string fields are validated structurally — e.g. `parse_name_with_owner` raises `ValueError` on bad shape (`qrspi_resolve.py:132-139`), `coerce_cap` rejects non-positive-int / bool (`:393-402`). **JSON-Schema (`jsonschema` lib) is NOT used in Python.** JSON-Schema-shaped objects exist only on the **JS side** as harness `StructuredOutput` schemas (`TICKETS_SCHEMA`, `WORKER_SCHEMA`, `IMPL_SETUP_SCHEMA`, etc., `.claude/workflows/qrspi-batch.js:182-453`), but the resolve/config/critic envelopes deliberately AVOID StructuredOutput (the weak worker stalled on it) and are validated by hand-rolled JS parsers (`parseConfigEnvelope`, `parseCriticsEnvelope`, `parseLandVerdict`). No `.qrspi/` `*schema*.json` file exists; `.qrspi/templates/` holds markdown artifact templates only.

Searches attempted: `find .qrspi -name "*schema*"`; `grep -rln "jsonschema|choices=|StructuredOutput|VALID_|ALLOWED_" scripts/*.py`.

**Evidence:**

```python
ARTIFACTS = ["questions", "research", "design", "structure", "plan", "worktree"]
...
parser.add_argument("--artifact", required=True, choices=ARTIFACTS, ...)
```

— `scripts/qrspi_persist.py:52, 101-102`
**Dependencies:** `argparse.choices` is the enum gate; `RESOLVE_ACTIONS` set (JS) gates actions; pure coercion helpers (`coerce_cap`) reject bad values.
**Implicit contracts:** Enums are validated via `argparse choices` (fail at parse with non-zero exit) or an explicit whitelist set/coercion. There is NO `jsonschema`-based runtime validator to plug into in Python — an event schema would either reuse `argparse choices` enums or add a new validation helper. Bad values fail closed (non-zero exit / ok:false), never silently accepted.

## Q13: What is the unit-test convention for an event emitter / log rotator / retention cleaner, and how does `run_tests.py` discover tests?

**Answer:** Convention (per CLAUDE.md "stdlib-only `_test.py` siblings"): each `scripts/<name>_test.py` is a standalone `unittest`-based file (no pytest), imports the module under test by bare name (siblings share the dir, e.g. `import qrspi_metrics_append as a`), exercises **pure helpers against `tempfile` temp dirs**, runs via `if __name__ == "__main__": unittest.main()`, and exits 0 on success. `scripts/run_tests.py` `discover_tests` globs `scripts/*_test.py` (any basename ending `_test.py`, sorted, optional substring filter) and `run_one` runs each as its own subprocess `[python, path]` with a 180s timeout, treating non-zero/timeout as FAIL (`run_tests.py:36-75`). The representative `qrspi_metrics_append_test.py` shows the pattern: `LedgerPathTest` asserts the pure path helper (incl. the no-double-nesting guard), `WrapEnvelopeTest` asserts the pure envelope wrapper and input-immutability. A new emitter/rotator/cleaner should follow this: pure-core tests against temp dirs, named `qrspi_<thing>_test.py` so `run_tests.py` auto-discovers it (also wired into CI `.github/workflows/tests.yml`).

**Evidence:**

```python
def discover_tests(scripts_dir=SCRIPT_DIR, pattern=None):
    names = sorted(n for n in os.listdir(scripts_dir) if n.endswith("_test.py"))
    if pattern:
        names = [n for n in names if pattern in n]
    return [os.path.join(scripts_dir, n) for n in names]
```

— `scripts/run_tests.py:36-48`
**Dependencies:** `run_tests.py` discovers/subprocess-runs every `scripts/*_test.py`; tests import their target module + `qrspi_paths` by bare name (sibling sys.path).
**Implicit contracts:** Tests must be stdlib-only, exit 0/non-zero, run standalone as `python3 scripts/<name>_test.py`, and live as a sibling named `*_test.py` (or `run_tests.py` won't find them, and CI won't gate on them). Pure helpers must be separable from I/O so tests hit temp dirs (the `tempfile` convention). `run_tests.py` and `run_tests_test.py` are deliberately excluded/guarded from being suite members (`:30-33`).

## Q14: What logging is emitted to stderr / a log file by qrspi CLI commands today, and how would `QRSPI_LOG_LEVEL` filtering + dual stderr+`cli.log` output integrate with current entry points?

**Answer:** There is **no leveled logging and no `cli.log` today.** The `qrspi_*` pipeline scripts emit **only a single JSON envelope to stdout** and reserve stderr for nothing structured (the design scripts keep stdout clean for the JS parser). The only stderr usage in `scripts/` is in **non-pipeline / eval / one-off** tools: `meta_agent.py:50` (`print("meta_agent: %s", file=sys.stderr)`), `qrspi_research_digest.py:104-116` (`sys.stderr.write(...)` for I/O errors), `eval_all.py`, `diagnose.py`, `revise.py` — none use the `logging` module; `grep "logging\."` finds none. On the JS side, the orchestrator emits human-readable progress via the **injected `log(...)` harness global** (used ~throughout, e.g. `:2620`, `:2704`) — it is NOT defined in the file and is not leveled. There is **no `QRSPI_LOG_LEVEL` env var anywhere** (grep returns nothing). So a leveled `QRSPI_LOG_LEVEL` (debug/info/warn/error) + dual stderr+`cli.log` sink would be entirely NEW: the integration point in Python is each script's entrypoint (add a logger configured from the env var, writing structured lines to stderr AND appending to `cli.log`); in JS it would wrap/replace the `log()` calls.

Searches attempted: `grep -rn "sys.stderr|logging.|QRSPI_LOG_LEVEL|logLevel|cli.log"` over `scripts/` and `.claude/`.

**Evidence:**

```python
sys.stderr.write("research input not found or unreadable: %s\n" % exc)
```

— `scripts/qrspi_research_digest.py:104` (ad-hoc stderr; no level, no logging module, no cli.log)
**Dependencies:** pipeline scripts → stdout JSON envelope only; JS orchestrator → injected `log()` global. No shared logging module exists.
**Implicit contracts:** stdout of pipeline scripts is RESERVED for the JSON envelope (callers parse it) — any human/log output MUST go to stderr or a separate file, never stdout. There is no existing leveled-logging facility to extend; `QRSPI_LOG_LEVEL` and `cli.log` are greenfield. The `log()` JS global may be a no-op in the sandbox, so JS-side logging must tolerate its absence.

## Q15: How is `ticket_id` / `phase` / `trace_id` context available at log-emission sites, so required log context can always be attached?

**Answer:** At JS orchestrator sites: `ticket_id` is `t.id` / `id` (threaded through `runPhase(name, agentType, prompt, existing, id, phaseLabel, ...)`, `:1290`), `phase` is the `phaseLabel`/`name` argument, and the only correlation id is the module-level `runId` (`:118-126`) — there is **no `trace_id`** (see Q3). At Python script sites: `ticket_id` arrives as `--ticket`, `phase` as either `--artifact`/`--phase` flags or is implicit; `runId` arrives as `--run-id` (only the metrics appender takes it today). The established pattern for "always attach context" is `qrspi_metrics_append.wrap_envelope(record, ticket, timestamp, run_id)` which **injects `ticketId` + `timestamp` + `runId` onto every ledger line, appender-wins over any pre-existing value** (`qrspi_metrics_append.py:67-79`). That is the template a log emitter should follow: take ticket/phase/(trace) as explicit flags and stamp them onto every emitted line. Since `trace_id` does not exist, it would have to be introduced (likely derived from / alongside `runId`, generated with `crypto` in JS per the no-`Date.now()` rule).

**Evidence:**

```python
def wrap_envelope(record, ticket, timestamp, run_id):
    line = dict(record)
    line["ticketId"] = ticket
    line["timestamp"] = timestamp
    line["runId"] = run_id
    return line
```

— `scripts/qrspi_metrics_append.py:67-79`
**Dependencies:** JS threads `t.id`/`phaseLabel`/`runId` into `runPhase` and into the `--ticket`/`--run-id` flags of `qrspi_metrics_append.py`.
**Implicit contracts:** Context is passed as explicit CLI flags JS→Python (never env/shared object); the appender is the "single envelope authority" that stamps context onto every line (its values win). `ticketId`+`phase`+`runId` are always available; `trace_id`/`span_id` are NOT (greenfield). Any "always attach context" emitter must take these as flags and stamp them per line, mirroring `wrap_envelope`.

---

## Discovered Patterns

- **Self-locating script triad.** Every durable-state script (`qrspi_persist.py`, `qrspi_metrics_append.py`, `qrspi_resolve.py`, `qrspi_config.py`) follows the same skeleton: `ENGINE_ROOT` from `__file__` for sibling imports, host root via `qrspi_paths.resolve_repo_root(validate=False)` (git-common-dir-first, MAIN checkout even from a worktree), short-token argparse flags, pure I/O-free core + thin I/O shell, one JSON envelope `{ok, ..., error?}` on stdout, `return 0/1`. A new event emitter MUST follow this skeleton.
- **Fail-closed, report-once, never-retry.** Both scripts (ok:false envelope, no internal retry) and worker prompts ("HARD STOP, do NOT retry"). This is the dominant error posture; it directly contradicts the Q7 premise of an existing retry/backoff policy (none exists in the pipeline).
- **Per-ticket worktree isolation as the concurrency model.** No locks anywhere; safety comes from each ticket owning `.worktrees/<id>/.qrspi/<id>/`. The existing `critic-metrics.jsonl` ledger is per-ticket for exactly this reason.
- **Existing JSONL append precedent.** `qrspi_metrics_append.py` already implements append + non-empty-verify + per-line envelope stamping (`ticketId`/`timestamp`/`runId`). It is the single closest analog for the proposed event log — an event emitter is essentially a generalization of it.
- **Nested-config-via-dedicated-resolver.** `critics` (read by `qrspi_critics_config.py`) is the precedent for a nested config block; the flat `--key`/`parseConfigEnvelope` path is string-only and cannot carry nested objects. `load_ci_revise_cap` shows the simpler "read parsed dict directly + coerce" path for a flat key.
- **Envelope-authority pattern.** The writer (appender) stamps correlation/context fields and its values WIN over caller-supplied ones — the single source of truth for those fields.
- **Pure-core + temp-dir tests, auto-discovered.** `run_tests.py` globs `scripts/*_test.py`; tests import siblings by bare name and exercise pure helpers against `tempfile` dirs.

## Inconsistencies

- **Q7 premise vs. reality.** The questions reference an exponential-backoff retry policy "already defined in the pipeline config" that the retry events must follow. **No such policy exists in the QRSPI pipeline.** The only backoff is in `scripts/grade.py` (the eval-judge harness, a documented non-functional placeholder), and the pipeline's explicit posture is "never retry / report once". The closest bounded-retry mechanism is the integer `ciReviseCap` / `CI-Revise-Attempt` trailer counter — a count, not a timed backoff.
- **Trace/span propagation does not exist.** Q3/Q15 assume `trace_id`/`span_id`/`parent_span_id` propagation; the codebase has only `runId` (one flat per-invocation id) plus `ticketId`/`phase`. Nested-operation span linkage is entirely absent.
- **`config.json` `--key` reader cannot read nested keys, but the example file already nests `critics`.** The flat `--key` CLI + JS `parseConfigEnvelope` rejects non-string values, yet `critics` is a nested block — resolved only by a separate dedicated resolver, not the `--key` path. A reader for `observability.*` must use the dedicated-resolver pattern, not the documented single-key reader.
- **`qrspi_config.py` self-locates differently from its siblings.** It uses `Path(__file__).resolve().parents[1]` (`:29`) instead of `qrspi_paths.resolve_repo_root(...)` like `qrspi_persist.py`/`qrspi_metrics_append.py`/`qrspi_resolve.py`. From a worktree this would resolve to the WORKTREE root, not the MAIN checkout — a latent divergence from the documented git-common-dir-first convention (works today only because config reads are best-effort and the worktree also has a `.qrspi/config.json` symlink/copy is NOT guaranteed).
- **No `fsync`/locking despite "crash-safe" framing.** Q9 asks for a crash-safe append pattern to match; the existing `qrspi_metrics_append.append_line` relies on `O_APPEND` + close-flush + non-empty-verify only — no `fsync`, no atomic rename. The only atomic primitive (`os.replace`) is in an unrelated whole-file cache writer. "Crash-safe" durability stronger than close-flush has no precedent to copy.
- **`STAGE_ROOT` duplicated.** `/tmp/phase-stage` is hard-coded in both `qrspi_persist.py:57` and the JS `stg()` helper (`.claude/workflows/qrspi-batch.js:633`), kept in sync by comment only — a drift risk any new staging consumer inherits.
