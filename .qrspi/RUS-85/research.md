# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Q1: At what points in a phase's execution path are phase start, phase end, success, failure, and retry currently signaled (return values, exceptions, status fields), so the new event emissions can be hooked there?

**Answer:** A single phase runs through `runPhase(name, agentType, prompt, existing, id, phaseLabel, criticConfig)` in `.claude/workflows/qrspi-batch.js`. It is a **boolean-returning** function — there is no event emission, no status field, and no structured start/end signal today. The signaling surface is:

- **Phase start / reuse:** the `existing[name]` early-return logs `reusing existing ${name}.md` and returns `true` (resume skip). The produce `agent()` spawn is the de-facto start.
- **Success:** `return true` at the end, only after the `persistArtifact()` gate succeeds. The line `log(... → saved ${p.bytes}B ...)` is the only success marker.
- **Failure:** every failure path is a `log(...)` line followed by `return false` — producer returns `null`, N-select stage fails, node-check fails (`!nc.ok`), critic loop fails (`!cr.ok`), or persist fails (`!p || !p.ok`). There are **no exceptions** thrown inside `runPhase`; failure is a falsy return.
- **Retry:** there is **no retry inside `runPhase`**. Per `docs/testing-dynamic-workflows.md:288-311`, transient `agent()` retry was deliberately withdrawn — the `agent()` seam returns a bare `null` with the error discarded, so a unit is treated as not-done and recomputed on a re-run (the resume guarantee), never retried in-process. The only "retry"-shaped loop is the design-critic `revise` round loop in `runCriticPanelLoop` (not in `runPhase` proper).

The hook points for new emissions are: the `existing[name]` branch (reuse/skip), immediately after entry (start), each `return false` site (failure), and just before `return true` (success).

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
  if (!p || !p.ok) {
    log(`  ${id}: ${name} reported done but no artifact was staged/persisted — ${p?.error ?? 'no result'} (stopping this ticket)`)
    return false
  }
  log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
  return true
}
```

— `.claude/workflows/qrspi-batch.js:1305-1376`

**Dependencies:** `runPhase` is called by the phase finalize handlers (`doDesign`, `doPlan`, `doImplementation` — `phase('Design')` at :1529, `phase('Plan')` at :1650, `phase('Implementation')` at :1749). It depends downstream on `agent()` (harness-injected, non-deterministic), `runCriticPanelLoop`, `runNodeCheck`, `runDesignSelectLoop`, and `persistArtifact`.
**Implicit contracts:** Callers treat `false` as "stop this ticket this run" (fail-closed), never as a thrown error. `persistArtifact` is the *single post-validation success gate* — a phase is "done" iff a non-empty artifact landed (see Q9). There is no notion of "phase duration" measured anywhere; workflow scripts forbid `Date.now()` (`.claude/workflows/qrspi-batch.js:130`), so any duration timing for events must come from a Python helper at write time, not from JS.

## Q2: How does a phase invocation currently obtain the `ticket_id`, `phase`, and `actor` (agent vs user) values that each event must carry, and where in the call path are those values already in scope?

**Answer:**
- **`ticket_id`:** the ticket object `t` (with `t.id`, a string like `RUS-85`) is iterated in the main loop `for (let i = 0; i < tickets.length; i++)` and threaded into every handler. Inside `runPhase` it is the `id` parameter. Every persist/append shell-out already passes `--ticket ${id}` / `--ticket ${t.id}`.
- **`phase`:** two distinct phase concepts coexist. (1) The artifact/phase **name** (`name` param of `runPhase`: one of `questions|research|design|structure|plan|worktree`, plus `implementation`). (2) The harness **phaseLabel** (`phase('Design')`, `phase('Resolve')`, `phase('Finalize')` etc.) — a coarse UI grouping passed as `{ phase: phaseLabel }` to `agent()`. The resolver's `decision.phase` (`design|plan|implementation`) is the lifecycle phase. All three are in scope in the handlers.
- **`actor` (agent vs user):** **NOT FOUND as an explicit field.** The codebase has no `actor`/`who` discriminator. The closest concepts: every automated step runs through `agent(prompt, { label, phase, agentType })` (the LLM worker), and `qrspi_metrics_append.py` injects `runId` to scope a *run*. The Linear "assigned to a user" fact is passed as `--assigned` to `qrspi_resolve.py` but is not an event actor. Distinguishing agent vs user is not represented anywhere; it would be a new convention.

**Evidence:**

```js
const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
```

— `.claude/workflows/qrspi-batch.js:1310`

```js
for (let i = 0; i < tickets.length; i++) {
  ...
  const a = r.decision.action
  log(`  ${t.id}: decision=${a} — ${r.decision.reason}`)
```

— `.claude/workflows/qrspi-batch.js:2659` (loop) and the dispatch switch at :2670-2693

**Dependencies:** `t.id` originates from the Query phase ticket list (`TICKETS_SCHEMA`, `.claude/workflows/qrspi-batch.js:197-215`, fields `id,title,status,createdAt`). The resolver envelope carries `decision.phase` (`scripts/qrspi_resolve.py` `build_envelope`).
**Implicit contracts:** Ticket id is always a string and always available as `id`/`t.id`. `phaseLabel` is harness-UI-only (it groups workers); the *real* lifecycle phase for an event should be the `runPhase` `name` or the resolver `decision.phase`, not `phaseLabel`. There is no actor model — any event `actor` field is greenfield.

## Q3: How are trace/span identifiers (a per-run id) currently generated or propagated in the orchestrator, given the prior `runId` work, and is there an existing id that can serve as `trace_id`?

**Answer:** Yes — **`runId` is the existing per-invocation id and is the natural `trace_id`.** It is computed ONCE at the top of `qrspi-batch.js`: `process.env.QRSPI_RUN_ID` when the harness exports one, else `crypto.randomUUID()`, else a `crypto.getRandomValues`-derived `run-<hex>`, else the constant `'run-fallback'`. Workflow scripts **forbid `Date.now()`/`Math.random()`** (they break resume), which is why the fallback chain uses crypto, not a timestamp. `runId` is propagated as a string into the metrics ledger via `--run-id '${runId}'` (the single existing consumer pattern, RUS-78). There is **no span/per-phase sub-id** today — only the one run-level id. A per-phase `span_id` would be new.

**Evidence:**

```js
const runId =
  (typeof process !== 'undefined' && process.env && process.env.QRSPI_RUN_ID) ||
  (typeof crypto !== 'undefined' && crypto.randomUUID && crypto.randomUUID()) ||
  (typeof crypto !== 'undefined' &&
    crypto.getRandomValues &&
    `run-${Array.from(crypto.getRandomValues(new Uint8Array(8)))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('')}`) ||
  'run-fallback'
```

— `.claude/workflows/qrspi-batch.js:133-141`

```js
... python3 ${engineCmd('scripts/qrspi_metrics_append.py')} --ticket ${id} --run-id '${runId}' --record "$(cat ...)" ...
```

— `.claude/workflows/qrspi-batch.js:995`

**Dependencies:** `runId` is consumed by `qrspi_metrics_append.py` (`--run-id`, `wrap_envelope(... run_id)`) and scoped-reported by `scripts/qrspi_critic_summary.py` (per the comment at :124-126).
**Implicit contracts:** "`runId` always present, always a string" (`.claude/workflows/qrspi-batch.js:128`). The append helper enforces `--run-id` as required and always stamps it as the field `runId` (`scripts/qrspi_metrics_append.py:111-113, 78`). Any event log should reuse this same `runId` as `trace_id` for cross-artifact correlation; a memory note (`qrspi-batch-runid-datenow-bug.md`) records that the `Date.now()/Math.random()` fallback was a bug already fixed — do not reintroduce it.

## Q4: What command/entry interface do the existing self-locating scripts (`qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_pr_body.py`) expose, so an event-emitter script can follow the same invocation and repo-root self-location convention?

**Answer:** All self-locating QRSPI scripts share one rigid convention:
1. `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))` + `sys.path.insert(0, ENGINE_ROOT)` for sibling imports (NEVER a host path).
2. `import qrspi_paths` and resolve the **host checkout root** via `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` at module load (git-common-dir first → MAIN checkout even from a worktree; `__file__` parent last resort). `validate=False` at import keeps `gh` off the import path.
3. `argparse` CLI with short tokens only (`--ticket`, `--artifact`, `--record`, `--run-id`, `--repo-root`); the qrspi-laden destination path is **computed by the script**, never typed by the caller.
4. **Output: a single JSON envelope on stdout** with `{ ok, ... , error? }`, printed via `json.dump(env, sys.stdout, indent=2)` + `print()`, exit `0` on `ok` else `1`. Failure reported ONCE as `ok:false` (never retried).
5. A `--repo-root` override flag (validated against `gh repo view`).

An event-emitter script should mirror `qrspi_metrics_append.py` most closely (it is the existing append-to-JSONL precedent — see Q6/Q14).

**Evidence:**

```python
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)
import qrspi_paths  # noqa: E402
REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)
```

— `.claude/workflows/qrspi-batch.js` callers + `scripts/qrspi_persist.py:45-50`, `scripts/qrspi_metrics_append.py:52-55`, `scripts/qrspi_resolve.py:50-58`

```python
    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if error is None else 1
```

— `scripts/qrspi_persist.py:131-133` (identical tail in `qrspi_resolve.py:575-577`, `qrspi_metrics_append.py:147-149`)

**Dependencies:** All three depend on `scripts/qrspi_paths.py` (`resolve_repo_root`, `engine_root`, `HostRootError`). The JS side parses each envelope with a `parse*Envelope` function (`extractJsonObject` brace-scanner, `.claude/workflows/qrspi-batch.js:237-253`).
**Implicit contracts:** The script OWNS every `qrspi`-token path (computed, never echoed by the weak worker model — the whole point of Fix A). Callers pass only short tokens. The envelope tail format (`indent=2` + trailing newline) is part of the contract some producer tests pin (see `docs/testing-dynamic-workflows.md:163-182`).

## Q5: How do existing scripts read configuration values like `ciReviseCap`, and what is the documented limitation of the config reader that bounds how the configurable log-rotation size, retention, and log-level keys can be expressed?

**Answer:** `scripts/qrspi_config.py` is the config reader. Its hard limitation: **it reads exactly ONE FLAT top-level key — there is NO dot-path / nested-key support.** `read_config(repo_root)` parses `<repo>/.qrspi/config.json` to a dict (best-effort: returns `{}` on any `OSError`/`ValueError`, never raises), and `select_value(config, key, default)` returns `config[key]` when present-and-truthy else the default. The CLI is `python3 scripts/qrspi_config.py --key <name>` → `{ "ok", "key", "value": <str|null> }`. Note `DEFAULTS = {"linearProject": "QRSPI"}`; unknown keys default to the **empty string** and the documented value type is string (`value: <str|null>`).

`ciReviseCap` is read NOT via `qrspi_config.py`'s CLI but via `qrspi_resolve.py.load_ci_revise_cap()`, which calls `qrspi_config.read_config(repo_root)` then `config.get("ciReviseCap")` and coerces with `coerce_cap()` (positive int; bool/non-int/non-positive → default 3). So the pattern for a numeric/typed key is: read the flat dict in Python, then coerce/validate in a pure helper. The JS-side `parseConfigEnvelope` **rejects non-string values** (project memory `qrspi-config-reader-single-key-only.md`): so a config value read *through the JS envelope path* must be a string.

**Implication for log-rotation size / retention / log-level keys:** they must be expressed as **flat top-level keys** (e.g. `logRotateBytes`, `logRetention`, `logLevel`), NOT a nested `observability: {...}` block — `qrspi_config.py` cannot read a nested path. If read in Python they can be coerced from any JSON scalar (like `coerce_cap`); if surfaced through the JS `parseConfigEnvelope` they must be strings. (Contrast: the `critics` block IS nested, but it is read by a *different* resolver, `scripts/qrspi_critics_config.py`, not `qrspi_config.py`.)

**Evidence:**

```python
def select_value(config: dict, key: str, default: str) -> str:
    value = config.get(key)
    return value if value else default
```

— `scripts/qrspi_config.py:36-42`

```python
def coerce_cap(value):
    if isinstance(value, bool) or not isinstance(value, int):
        return CI_REVISE_CAP_DEFAULT
    return value if value > 0 else CI_REVISE_CAP_DEFAULT

def load_ci_revise_cap(repo_root=REPO_ROOT):
    config = qrspi_config.read_config(repo_root)
    return coerce_cap(config.get("ciReviseCap"))
```

— `scripts/qrspi_resolve.py:394-412`

**Dependencies:** `qrspi_config.read_config` is shared by `qrspi_resolve.py` (`load_ci_revise_cap`). `.qrspi/config.json` is gitignored; `.qrspi/config.example.json` documents every key. The `ciReviseCap` doc lives in the `$comment_ci` example key.
**Implicit contracts:** "single top-level key only, no dot-path" (`scripts/qrspi_resolve.py:407-409` comment, ref: project memory). Truthy-falsy fallback: `select_value` treats `0`/`""`/`false` as absent (returns default) — a caveat for any numeric key that legitimately could be 0, which is exactly why `ciReviseCap` uses its own `coerce_cap` instead of `select_value`.

## Q6: How is the `.qrspi/<ticket-id>/` artifact directory currently created and located per ticket, and does an analogous mechanism exist (or need to be added) for the `.qrspi/observability/` directory the event log writes to?

**Answer:** The per-ticket dir is `<repo_root>/.worktrees/<ticket>/.qrspi/<ticket>/`, computed by `dest_path()` in `qrspi_persist.py` and created on demand by `os.makedirs(os.path.dirname(dest), exist_ok=True)` inside `persist()`. The same pattern is reused by `qrspi_metrics_append.py.ledger_path()` (which appends `critic-metrics.jsonl` into that dir) with `os.makedirs(..., exist_ok=True)` in `append_line()`. So the precedent is: **compute a canonical path off the resolved host root, then `os.makedirs(dirname, exist_ok=True)` lazily on first write.** There is NO eager directory provisioning step anywhere.

**`.qrspi/observability/` does NOT exist** — confirmed: `find` returns no such dir and `grep` finds no `observability` directory/path code (only the word in prose/comments and one RUS-21/RUS-28 research note about MCP observability being absent). It must be **added new**, but the mechanism is fully analogous: a new emitter script would compute `<repo_root>/.qrspi/observability/events.jsonl` (or a per-ticket equivalent) and `os.makedirs(dirname, exist_ok=True)` on first append. **Decision point for design:** the existing JSONL ledger is **per-ticket** (`.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`), whereas the question's `.qrspi/observability/events.jsonl` is a **single shared, repo-root-level** file — a different layout (repo-root `.qrspi/`, not a worktree's `.qrspi/<id>/`), which has concurrency implications (see Q8).

**Evidence:**

```python
def dest_path(repo_root, ticket, artifact):
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket,
                        "%s.md" % artifact)
def persist(src, dest):
    ...
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(src, dest)
```

— `scripts/qrspi_persist.py:67-84`

```python
def ledger_path(repo_root, ticket):
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket,
                        "critic-metrics.jsonl")
def append_line(path, ledger_line):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(ledger_line) + "\n")
```

— `scripts/qrspi_metrics_append.py:60-90`

**Dependencies:** Both compute the root via `qrspi_paths.resolve_repo_root`. A new `.qrspi/observability/` writer would depend on the same module.
**Implicit contracts:** Dirs are created lazily by the writer, never assumed to exist. The host root MUST come from `resolve_repo_root` (git-common-dir-first) — `qrspi_metrics_append.py:20-28` explicitly warns that self-locating from `__file__` would yield the WORKTREE root and double-nest the path to `.worktrees/<id>/.worktrees/<id>/.qrspi/...`. A repo-root-level `.qrspi/observability/` must be derived from the resolved MAIN-checkout root, NOT a worktree root.

## Q7: Where is the exponential-backoff policy "already defined in the pipeline config" that retry-interval events must reflect, and in what form (key names, defaults) is it stored?

**Answer:** **NOT FOUND as a pipeline-config exponential-backoff policy.** There is no `backoff`/`retryInterval`/`exponential` key in `.qrspi/config.json` / `.qrspi/config.example.json`, and the CI-revise path does **not** use exponential backoff. What exists in the CI-revise path is a **count cap, not an interval/backoff**: `ciReviseCap` (flat key, default 3) bounds *consecutive* red-CI auto-revises in `qrspi_resolve_state.resolve()`. There is no inter-attempt delay — the resolver just switches `revise → wait` once `attempt >= ci_revise_cap`. Searches: `grep -rn "backoff|retryInterval|exponential"` over `scripts/`, `.qrspi/`, `docs/`.

The ONLY exponential-backoff implementation in the repo is in the **eval/judge harness, unrelated to the QRSPI pipeline**: `scripts/grade.py` `call_with_retry()` retries a judge-client call up to `JUDGE_MAX_ATTEMPTS = 3` with `time.sleep(JUDGE_BACKOFF_BASE * (2 ** attempt))`, `JUDGE_BACKOFF_BASE = 1.0` second. That is for LLM-judge transient failures (`scripts/grade.py:865-882`, constants at :652-653), not the phase pipeline. `docs/testing-dynamic-workflows.md:288-311` further records that a transient-retry-with-backoff classifier for the `agent()` seam was **deliberately withdrawn** as unbuildable.

So if a "retry-interval event must reflect an exponential-backoff policy already in pipeline config," that premise does not match the current code: the pipeline retry policy is a *consecutive-failure count cap* (`ciReviseCap`, default 3), with no time-interval/backoff. This is a candidate **inconsistency to flag** for the design phase.

**Evidence:**

```python
JUDGE_MAX_ATTEMPTS = 3
JUDGE_BACKOFF_BASE = 1.0  # seconds; doubled each retry
...
            if attempt < JUDGE_MAX_ATTEMPTS - 1:
                time.sleep(JUDGE_BACKOFF_BASE * (2 ** attempt))
```

— `scripts/grade.py:652-653, 875-881`

```python
    fci = ci_state(phases, frontier)
    if fci == "red":
        attempt = ci_revise_attempt_of(phases, frontier)
        if attempt < ci_revise_cap:
            return decision("revise", phase=frontier, ciFailing=True, ...)
        return decision("wait", phase=frontier, ciFailing=True, ciGaveUp=True, ...)
```

— `scripts/qrspi_resolve_state.py:289-303`

**Dependencies:** `ciReviseCap` resolved by `qrspi_resolve.py.load_ci_revise_cap` → `qrspi_resolve_state.resolve(state, ci_revise_cap=...)`. The attempt count is tracked via the `CI-Revise-Attempt: N` head-commit trailer (gathered by `qrspi_pr_state.py`, written by `doRevise`/`qrspi_revise_amend.py`).
**Implicit contracts:** Retry bounding in the pipeline is by *count* (3) not *interval*; the counter has a read-side reset (gather forces `0` when not red) and a writer-side reset (non-CI amend writes `CI-Revise-Attempt: 0`). Any "retry-interval / backoff" event has no existing source-of-truth to read; it would either be newly defined or reuse `grade.py`'s judge constants (which are out of the pipeline path).

## Q8: How is concurrency across tickets handled today (multiple worktrees / batch workers running in parallel), and what does that imply for concurrent appends to the single `.qrspi/observability/events.jsonl` file?

**Answer:** Within a single `qrspi-batch` run, tickets are processed **strictly sequentially** — `for (let i = 0; i < tickets.length; i++) { ... }` with `await` on each handler — so there is no in-run parallelism across tickets. **Isolation is by worktree**: each ticket gets `.worktrees/<id>/` (`.claude/CLAUDE.md` "Worktrees" section), and the existing JSONL ledger is *per-ticket per-worktree* (`.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`), so two tickets never write the same ledger file today. However, the project explicitly supports **multiple agents on different tickets concurrently** ("This allows multiple agents to work on different tickets concurrently") — i.e. multiple `qrspi-batch`/`qrspi-work` *processes* can run in parallel, each its own `runId`.

**Implication for a single shared `.qrspi/observability/events.jsonl`:** this is the **first shared cross-ticket sink** the system would have — it breaks the current per-worktree isolation invariant. Concurrent OS-level appenders to one file are at risk of interleaved/torn lines. The current `append_line` uses a plain `open(path, "a")` + `fh.write(json.dumps(line) + "\n")` (`qrspi_metrics_append.py:88-90`) with **no file lock**. On POSIX, a single `write()` under `O_APPEND` of a line smaller than `PIPE_BUF` (4096 bytes) is atomic, but Python's buffered `write` is not guaranteed to be a single syscall, and lines may exceed 4096 bytes — so the current pattern is NOT safe for concurrent writers as-is. A shared events file would need either per-ticket files (preserving isolation, matching the existing ledger layout) or an explicit lock/atomic-append mechanism — neither exists today.

**Evidence:**

```js
for (let i = 0; i < tickets.length; i++) {
  ...
  const a = r.decision.action
  ...
  results.push(res)
```

— `.claude/workflows/qrspi-batch.js:2659-2700` (sequential, awaited)

```python
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(ledger_line) + "\n")
```

— `scripts/qrspi_metrics_append.py:88-90` (no lock; per-ticket path so today never contended)

**Dependencies:** Worktree isolation is set up by `qrspi_resolve.py.setup_worktree` (`.worktrees/<id>`). Each run has one `runId`.
**Implicit contracts:** Today every durable write target is per-ticket-scoped, so no cross-ticket write contention exists. A single repo-root `events.jsonl` would be a NEW shared-resource invariant; the safe-by-construction option that matches existing precedent is a per-ticket events file under `.worktrees/<id>/.qrspi/<id>/`. (Memory `dependent-tickets-need-blocker-edge.md` notes parallel batch runs on related tickets already cause divergent conflicts in shared files — reinforcing the risk of a single shared sink.)

## Q9: What does the codebase currently do when a phase process crashes mid-execution, and at what granularity are partial writes possible — i.e., what guarantees an append is "append-aligned, never rewritten" on crash?

**Answer:** The resume guarantee (`docs/testing-dynamic-workflows.md:229-264`) governs crashes: a mid-phase/mid-slice `agent()` failure surfaces as a bare `null`, `runPhase` returns `false`, and **nothing is persisted** because `persistArtifact` (→ `qrspi_persist.py`) is the *single post-validation success gate* that runs only after the producer + all critic/node-check stages pass. The producer writes to a **token-free staging path** (`/tmp/phase-stage/<id>/<name>.md`), never the canonical artifact path, so a crash leaves no half-written canonical artifact; `detect_existing` reads `False` for that unit on re-run and it recomputes. The honest caveat: `detect_existing` gates on **byte count only** (`os.path.getsize(...) > 0`), not structural validity — a present-but-garbage artifact reads `True` and would be skipped.

For **append alignment of a JSONL ledger** specifically: `append_line` opens in `"a"` mode and writes `json.dumps(line) + "\n"` as one buffered write, then re-reads to verify non-empty and count lines, failing CLOSED if the file is empty after the write. The "append-aligned, never rewritten" property comes from `"a"` (append) mode — it never truncates/rewrites prior lines — and the `\n`-terminated single write. There is **no fsync, no per-line checksum, and no lock**, so the guarantee is: prior lines are never rewritten (append mode), but a crash *during* a write could leave a final torn/partial line (no atomicity guarantee for a single buffered write that exceeds the OS atomic-append size). A JSONL reader must tolerate a trailing partial line.

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
```

— `scripts/qrspi_metrics_append.py:82-96`

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
```

— `scripts/qrspi_persist.py:74-85`

**Dependencies:** Resume decision feeds off `qrspi_resolve.py.detect_existing` (byte-count map on the `existing` envelope field) and `runPhase`'s `existing[name]` early-return.
**Implicit contracts:** "A truncated/aborted write reads as *recompute*, never as a false skip" (`docs/testing-dynamic-workflows.md:262-264`). Append mode never rewrites earlier bytes; no durability (fsync) or torn-line protection exists. Persist refuses zero-byte files (fail-closed). These bound how strong an "append-aligned, never rewritten" claim a new event log can honestly make.

## Q10: How do existing scripts behave when their target directory or file is missing, unwritable, or the path contains the `qrspi` token (the path-mangling failure Fix A addresses) — what is the precedent for failing loud vs degrading?

**Answer:** Two distinct, deliberate behaviors:
- **Fail LOUD (fail-closed) for the success path:** `qrspi_persist.py.persist()` returns an error (→ `ok:false`, exit 1) for missing/unreadable source (`"staged artifact not found or unreadable"`), empty source (`"staged artifact is empty"`), or empty-after-move destination — reported ONCE, never retried. `runPhase` turns that into `return false` (stop the ticket). `qrspi_resolve.py.main` wraps everything in `try/except` and emits ONE `ok:false` envelope with the verbatim `"%s: %s" % (type, exc)` on any infrastructure failure (`scripts/qrspi_resolve.py:564-573`), never partial-retry. `qrspi_paths.resolve_repo_root` raises `HostRootError` (fail loud) when a supplied/auto-detected root fails the `gh repo view` gate.
- **DEGRADE silently to a default for best-effort reads:** config/reviewer reads return `{}` on any `OSError`/`ValueError` and never raise (`qrspi_config.read_config`, `qrspi_resolve._read_reviewer_config`). These are explicitly "best-effort, must not break a resolve."

**The `qrspi`-token mangling (Fix A):** addressed by REMOVING the token from the model's hands — the agent writes to a token-free `/tmp/phase-stage/<id>/<name>.md` and the SCRIPT (self-locating) computes the canonical `qrspi` path. There is **no runtime detection of a mangled path**; the design *prevents* mangling rather than detecting it. `qrspi_metrics_append.py:20-28` additionally warns that resolving the root from `__file__` instead of git-common-dir would silently double-nest into a phantom `.worktrees/<id>/.worktrees/<id>/.qrspi/...` that the non-empty verify would still pass — so root resolution MUST be git-common-dir-first.

**Evidence:**

```python
    try:
        size = os.path.getsize(src)
    except OSError:
        return 0, "staged artifact not found or unreadable: %s" % src
    if size == 0:
        return 0, "staged artifact is empty: %s" % src
```

— `scripts/qrspi_persist.py:79-83` (fail-loud success path)

```python
    except Exception as exc:  # noqa: BLE001 - any failure is reported, not retried
        err_root = os.path.abspath(args.repo_root) if args.repo_root else REPO_ROOT
        ...
        env = build_envelope(worktree, None, {name: False for name in ARTIFACTS},
                             ok=False, error="%s: %s" % (type(exc).__name__, exc), ...)
```

— `scripts/qrspi_resolve.py:564-573`

**Dependencies:** Fail-loud envelopes are consumed by JS parsers that treat `ok:false` as a clean stop (`parseResolveEnvelope`, `.claude/workflows/qrspi-batch.js:259-264`). `HostRootError` from `qrspi_paths`.
**Implicit contracts:** Success-path I/O fails loud and once (`ok:false` + verbatim error, exit 1, no retry — "a clean stop is what keeps a weak model from spiralling," `qrspi_resolve.py:534-535`). Auxiliary reads (config/reviewers) degrade to defaults and never raise. New event-emission code should follow the same split: the EMIT must not crash a phase (best-effort/degrade, since logging is auxiliary), but its own self-test should report `ok:false` honestly.

## Q11: What is the existing stdlib-only unit-test convention (`scripts/*_test.py`, `scripts/run_tests.py`) and how do current tests exercise file-writing scripts without polluting the real repo (temp dirs, fixtures)?

**Answer:** Convention: every script has a `scripts/<name>_test.py` sibling, **stdlib `unittest` only** (no pytest), runnable standalone (`python3 scripts/<name>_test.py`, exits 0/non-zero). `scripts/run_tests.py` auto-discovers every `*_test.py` (sorted), runs each as its own subprocess with a 180s per-file timeout, prints PASS/FAIL, and exits non-zero if any fail; it is the CI gate (`.github/workflows/tests.yml`). Filter by substring (`run_tests.py resolve`), enumerate with `--list`.

File-writing scripts are tested against **`tempfile.TemporaryDirectory()`** roots — never the real repo:
- `qrspi_persist_test.py` builds a temp `self.root`, stages a file under `<root>/stage/...`, asserts `persist()` moves it to `dest_path(self.root, ...)`, and tests the failure modes (missing source → "not found", empty source → "empty", no bogus dest created). Pure helpers (`staging_path`, `dest_path`) are tested with literal string args (no I/O).
- `qrspi_metrics_append_test.py` **monkeypatches the resolver** to pin the root: `qrspi_paths.resolve_repo_root = lambda *a, **k: self.root` in `setUp`, restored in `tearDown` — so `main()` writes into a temp dir. It asserts append-not-overwrite (line 0 intact after a second call), envelope wrapping, and `runId` round-trip.

**Evidence:**

```python
class PersistTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
    def tearDown(self):
        self.tmp.cleanup()
```

— `scripts/qrspi_persist_test.py:48-54`

```python
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self._orig = qrspi_paths.resolve_repo_root
        qrspi_paths.resolve_repo_root = lambda *args, **kw: self.root
    def tearDown(self):
        qrspi_paths.resolve_repo_root = self._orig
        self.tmp.cleanup()
```

— `scripts/qrspi_metrics_append_test.py:66-76`

**Dependencies:** `run_tests.py` (`discover_tests`, `run_one`, `run_suite`) → subprocess per file. CI: `.github/workflows/tests.yml`.
**Implicit contracts:** Tests are stdlib-only, self-contained, never touch the real `.qrspi`/`.worktrees`. The split is "pure helpers tested with literal args + I/O tested against a temp dir / monkeypatched root." A new event-emitter test should follow `qrspi_metrics_append_test.py` exactly (monkeypatch `resolve_repo_root`, temp dir, assert append-not-overwrite). Auto-discovery means a new `_test.py` needs zero registration.

## Q12: How is the harness-coupled JS in `qrspi-batch.js` currently tested or contract-verified given it is deemed not unit-testable in isolation, and what seam would an event-emission change be verified against?

**Answer:** `qrspi-batch.js` is **dual-illegal outside the harness** (top-level `return`/`await`, harness-injected globals `agent()`/`parallel()`/`pipeline()`/`phase()`/`log()`/`args`/`budget`, only `export const meta`, no `import`/`require`/fs support — confirmed by the 2026-06-14 probe). So it is NOT unit-tested directly. Instead, the strategy (`docs/testing-dynamic-workflows.md`) is **Functional Core / Imperative Shell**: deterministic logic lives in tested Python; the JS shell is "starved of logic." The residual JS seam is verified two ways:
1. A **`node --check`-style syntax gate** (strip the lone `export`, async-wrap, compile) in CI.
2. **JS↔Python contract/golden fixtures (RUS-76, shipped):** `scripts/fixtures/contract_seam/<seam>/<variant>.json` are asserted by BOTH sides — producer side `scripts/qrspi_contract_fixtures_producer_test.py` (Python script emits the envelope byte-for-byte), consumer side `scripts/qrspi_contract_fixtures_consumer_test.py` (drives `scripts/contract_seam_runner.js`, a `node:vm` harness that loads `qrspi-batch.js` via strip-`export`+async-wrap+injected-globals and exercises the `parse*` functions). Coverage is all eight `parse*` seams.

**Seam an event-emission change would be verified against:** the same JS↔Python contract-fixture seam. Because the design forbids inlining new logic in JS, an event-emission change should be a new **Python emitter script** (`scripts/qrspi_<emit>.py`) with a `_test.py` sibling (Q11 pattern) — fully unit-testable. If the JS shell must *parse* the emitter's envelope, add a `parse*` function + a `contract_seam/<seam>/{wellformed,malformed}.json` fixture asserted on both sides; if the JS only fires the emitter (fire-and-forget, like the `qrspi_metrics_append.py` shell-out at :995), there is no new parse seam to pin and the only JS coverage is the syntax gate. The honest limitation (b) (`docs/testing-dynamic-workflows.md:174-182`): IO-bound `main()` serializers (resolve/restack/cleanup) are NOT pinned by the producer test — a future `main()` formatting change wouldn't be caught — so an emitter whose `main()` does real I/O has the same caveat.

**Evidence:**

```
- **Producer side:** scripts/qrspi_contract_fixtures_producer_test.py asserts each
  Python producer's actual output conforms (shape + byte-for-byte serialization) ...
- **Consumer side:** scripts/qrspi_contract_fixtures_consumer_test.py drives
  scripts/contract_seam_runner.js (a node:vm harness that loads qrspi-batch.js ...)
```

— `docs/testing-dynamic-workflows.md:135-144`

```js
... | python3 ${engineCmd('scripts/qrspi_metrics_append.py')} --ticket ${id} --run-id '${runId}' --record "$(cat /tmp/qrspi-metrics-${id}-${phase}.json)" >/dev/null && ...
```

— `.claude/workflows/qrspi-batch.js:995` (fire-and-forget shell-out precedent: no JS parse of its envelope)

**Dependencies:** Fixtures dir `scripts/fixtures/contract_seam/`; runner `scripts/contract_seam_runner.js`; both `_test.py` siblings auto-discovered by `run_tests.py`.
**Implicit contracts:** New deterministic logic goes in Python with a `_test.py`, never inline JS (`docs/testing-dynamic-workflows.md:109-114`). The contract guard is "as strong as the fixtures are complete" — each parser validates only the fields it dereferences. The metrics append is the precedent for a fire-and-forget durable write the JS does NOT parse back.

## Q13: What logging, if any, do the current CLI scripts and the batch orchestrator already emit (stderr prints, structured output, result envelopes), and what format do they use that the new structured JSON logs must coexist with or replace?

**Answer:** Three coexisting output channels today, none of them a structured event log:
1. **Orchestrator human log:** `qrspi-batch.js` calls the harness-injected `log(...)` (81 call sites) with **unstructured human-readable strings** (`  ${id}: ${name} → saved ${p.bytes}B`, `[${i+1}/${tickets.length}] ${t.id} → ${res.action}`). This is the operator-facing progress narration, NOT machine-parseable.
2. **CLI script stdout = single JSON envelope:** every self-locating script prints exactly one `{ ok, ..., error? }` JSON object on stdout (`json.dump(env, sys.stdout, indent=2)` + `print()`). This is the *result-envelope* contract the JS parses. Some workers also print single-line JSON (node-check: "ONE single-line JSON envelope", `.claude/workflows/qrspi-batch.js:706`).
3. **stderr for human/error notes:** only a few scripts print to stderr, and they are largely the **eval/diagnose harness** (`eval_all.py`, `diagnose.py`, `meta_agent.py`, `revise.py`) plus `qrspi_research_digest.py` (writes errors to `sys.stderr`). The QRSPI pipeline scripts themselves put errors INTO the stdout envelope (`error` field), not stderr.

The only **structured, machine-readable, line-oriented** sink that exists is the **JSONL critic-metrics ledger** (`critic-metrics.jsonl`, one JSON object per line). A new structured JSON event log most resembles this and should coexist with (a) the human `log()` narration (which it does not replace) and (b) the per-call result envelopes (which are request/response, not an event stream). It would be the second JSONL stream alongside `critic-metrics.jsonl`.

**Evidence:**

```js
  log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
```

— `.claude/workflows/qrspi-batch.js:1374` (representative of all 81 `log()` sites — free-form strings)

```python
    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if error is None else 1
```

— `scripts/qrspi_persist.py:131-133` (the universal CLI stdout envelope)

**Dependencies:** `log()` is harness-injected (no Node API). Envelopes parsed by `extractJsonObject`/`parse*`. The JSONL precedent is `qrspi_metrics_append.py`.
**Implicit contracts:** stdout of a pipeline script is RESERVED for the single result envelope (the JS brace-scanner extracts the first balanced `{...}`); a new emitter must NOT print extra JSON to a script's stdout or it will confuse the parser — diagnostics belong on stderr or in a separate file. The human `log()` stream is operator narration and is not a substitute for, nor substituted by, structured events.

## Q14: How does the batch orchestrator currently record per-ticket results (the `wait`/`advance`/`revise` result rows) and phase durations, if at all — is there an existing result-recording structure that the phase-gate event log should align with?

**Answer:** Per-ticket results are accumulated in an in-memory `results` array (`const results = []`, `.claude/workflows/qrspi-batch.js:2656`) and returned from the workflow as `return { ticketsProcessed: results.length, results, reconciliation }` (final line). Each row is a plain object built by the handlers / by `skip()`: the canonical shape is `{ ticketId, action, summary }`, optionally extended with `newStatus`, `prUrl`, `ciGaveUp`, `ciReviseBumpFailed`, `reconcileRetry`. Distinct `action` values recorded include `run_design|advance|submit|wait|revise|reset|land|entry_blocked` (from the resolver decision) plus orchestrator-synthesized `restack_conflict` and `errored`. `skip(t, decision, note)` builds the `wait`/`entry_blocked` rows (`:650-658`).

**Phase durations: NOT recorded.** There is no timing anywhere — `Date.now()` is forbidden in workflow scripts (`.claude/workflows/qrspi-batch.js:130`), so the in-memory `results` rows carry no duration/elapsed field, and the human `log()` lines carry none either. The CriticStepMetrics ledger records `rounds`/`terminalAction`/`findingsCount` but **not wall-clock duration**.

The existing **durable** result-recording structure the phase-gate event log should align with is the **`CriticMetricsLedgerLine` JSONL ledger**: `qrspi_metrics_append.py` wraps a record with injected `ticketId` + `timestamp` (UTC ISO-8601, generated at write time) + `runId` and appends one JSON line to `.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`. That envelope (`ticketId`, `timestamp`, `runId`, plus the record body) is the precedent shape — a phase-gate event log should mirror its envelope fields (ticket, timestamp, runId/trace_id) and its append-and-verify-non-empty mechanics. The in-memory `results` array is ephemeral (returned, not persisted); the JSONL ledger is the durable one.

**Evidence:**

```js
function skip(t, decision, note) {
  const res = { ticketId: t.id, action: decision.action, summary: note }
  if (decision && decision.ciGaveUp) res.ciGaveUp = true
  return res
}
```

— `.claude/workflows/qrspi-batch.js:650-658`

```js
const results = []
...
  results.push(res)
...
return { ticketsProcessed: results.length, results, reconciliation }
```

— `.claude/workflows/qrspi-batch.js:2656`, `:2700`, final line

```python
    line = dict(record)
    line["ticketId"] = ticket
    line["timestamp"] = timestamp
    line["runId"] = run_id
    return line
```

— `scripts/qrspi_metrics_append.py:75-79` (`wrap_envelope` — the durable envelope shape)

**Dependencies:** `results` rows originate from the dispatch switch (`.claude/workflows/qrspi-batch.js:2670-2693`) and `skip()`. The durable ledger is `qrspi_metrics_append.py` + the per-ticket `critic-metrics.jsonl`. Timestamp source: `datetime.now(timezone.utc).isoformat()` (`qrspi_metrics_append.py:133`).
**Implicit contracts:** Every result row carries `ticketId` + `action` + `summary` (the minimum the final-line log `[${i+1}/${tickets.length}]` reads). The appender is the **single envelope authority** — it injects `ticketId`/`timestamp`/`runId`, overriding any pre-existing values (`qrspi_metrics_append.py:67-79`). The timestamp is generated at write time in Python (NOT in JS, which has no `Date.now()`), which is exactly where a phase-gate event's timestamp must come from too.

---

## Discovered Patterns

- **Functional Core / Imperative Shell is the architectural law.** All deterministic logic lives in tested `scripts/*.py` with a `_test.py` sibling; `qrspi-batch.js` is a logic-starved shell that only shells out. Any new event-emission logic MUST be a Python helper, not inline JS (`docs/testing-dynamic-workflows.md:109-114`). This is the single strongest constraint on RUS-85's shape.
- **Self-locating script convention (uniform):** `ENGINE_ROOT` from `__file__` for sibling imports + `qrspi_paths.resolve_repo_root(cwd=os.getcwd())` (git-common-dir first) for the host root + argparse short-token CLI + single `{ ok, ..., error? }` JSON envelope on stdout (indent=2, trailing newline) + exit 0/1, fail-once-never-retry. Shared by `qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_metrics_append.py`, `qrspi_config.py`, `qrspi_pr_body.py`.
- **Append-only JSONL ledger already exists** (`critic-metrics.jsonl` via `qrspi_metrics_append.py`) — the direct, working precedent for an event log: per-ticket path, `os.makedirs(..., exist_ok=True)`, `open(..,"a")` + `json.dumps(line)+"\n"`, verify non-empty, fail-closed, envelope-wrap with `ticketId`/`timestamp`/`runId`. RUS-85 should clone this pattern wholesale rather than invent a new one.
- **`runId` is the established per-run correlation id** (crypto-derived, never timestamp-based), already threaded into the ledger as `runId`. It is the obvious `trace_id`.
- **stdout of a pipeline script is reserved for exactly one JSON envelope** (the brace-scanner extracts the first balanced `{...}`); diagnostics go to stderr or a separate file. A new event sink must be a file/stderr, not extra stdout JSON.
- **Timestamps are generated in Python at write time** (`datetime.now(timezone.utc).isoformat()`), never in JS, because workflow scripts forbid `Date.now()`/`Math.random()`.
- **Fail-loud (success path, `ok:false`+exit1, once) vs degrade-silently (auxiliary config/reviewer reads → `{}`) is a deliberate, consistent split.**
- **Test isolation pattern:** `tempfile.TemporaryDirectory()` + monkeypatching `qrspi_paths.resolve_repo_root` to pin the root; pure helpers tested with literal args. New `_test.py` files are auto-discovered (zero registration).

## Inconsistencies

- **Q7 premise mismatch (flag for design):** The question assumes an "exponential-backoff policy already defined in the pipeline config" that retry-interval events must reflect. **No such policy exists.** The pipeline's only retry bound is a *consecutive-failure COUNT cap* (`ciReviseCap`, default 3) with NO inter-attempt interval/backoff. The only exponential backoff in the repo is `grade.py`'s LLM-judge retry (`JUDGE_BACKOFF_BASE=1.0`, `JUDGE_MAX_ATTEMPTS=3`), which is in the eval/judge harness, NOT the QRSPI phase pipeline. `docs/testing-dynamic-workflows.md:288-311` further documents that a transient-retry-with-backoff classifier was deliberately *withdrawn* as unbuildable at the `agent()` seam. Any "retry-interval event" has no existing pipeline-config source of truth to read.
- **Q6/Q8 layout divergence:** The question names a single shared repo-root `.qrspi/observability/events.jsonl`, but the existing durable JSONL ledger is **per-ticket, per-worktree** (`.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`). A single shared file would be the system's first cross-ticket shared sink, breaking the current per-worktree isolation invariant and introducing concurrent-append risk that the current lock-free `open(.., "a")` does not handle. The codebase precedent argues for per-ticket event files unless concurrency is explicitly solved.
- **Two meanings of "phase" in scope simultaneously:** the `runPhase` artifact `name` (`questions|research|...|worktree`/`implementation`), the harness UI `phaseLabel` (`Design`/`Resolve`/`Finalize`), and the resolver lifecycle `decision.phase` (`design|plan|implementation`) are all "phase" but are different vocabularies. An event's `phase` field must pick one deliberately (the `runPhase` name or `decision.phase`, not the UI `phaseLabel`).
- **No `actor` (agent vs user) discriminator anywhere** — Q2's required `actor` field has no existing source; it is greenfield. The system models *runs* (`runId`) and *workers* (`agentType`/`label`), not human-vs-agent authorship.
- **No phase-duration timing exists** — `Date.now()` is forbidden in the JS shell, and no Python helper currently times a phase. The CriticStepMetrics ledger records round counts, not wall-clock. Emitting duration would require capturing start/end timestamps in Python (the timestamp source pattern exists; the *pairing* into a duration does not).
- **`detect_existing` byte-count caveat:** resume gates on "non-empty present," not "structurally valid" (`docs/testing-dynamic-workflows.md:266-272`) — a present-but-garbage artifact reads as done. Relevant if events are ever used to drive resume decisions.
