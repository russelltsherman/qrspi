# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Q1: Where in the pipeline are phase transitions (phase start, phase end, success, failure, retry) currently driven, and at which call sites would an event-emission hook need to be inserted so every transition produces an event?

**Answer:** Phase transitions are driven entirely by `.claude/workflows/qrspi-batch.js`. There is **no central state-machine in Python** — `qrspi_resolve_state.py` only *decides* the next action; the JS shell *executes* the transition. The single chokepoint for the planning-phase artifact transitions is `runPhase()` (qrspi-batch.js:512-532); the per-action dispatch is the `switch (a)` block in the main loop (qrspi-batch.js:1644-1662), and per-ticket success/failure terminates in the surrounding `try/catch` (qrspi-batch.js:1618-1675). The harness exposes a `phase(label)` global called at section boundaries (e.g. qrspi-batch.js:538 `phase('Resolve')`, :1633 `phase('Restack')`) and a `log()` global; both are injected by the Workflow runtime, not defined in the file.

Candidate hook sites, in order of leverage:
- `runPhase()` — wraps every planning artifact agent: start (line 517 before `agent()`), success (line 530-531), failure (lines 518-520 agent null, lines 526-528 persist failure). One hook here covers questions/research/design/structure/plan/worktree.
- The action dispatch `switch` (qrspi-batch.js:1644-1662) — covers the coarse actions run_design / advance / submit / reset / revise / land / wait / entry_blocked.
- The per-ticket `catch` (qrspi-batch.js:1671-1675) — the **only** failure-capture point for a thrown phase worker; see Q9.
- `qrspi_resolve.py` is *not* a transition driver — it is a one-shot read (worktree setup + gather + decision); it would be the place to emit a `decision` event but does not itself run phases.

**Evidence:**

```javascript
async function runPhase(name, agentType, prompt, existing, id, phaseLabel) {
  if (existing && existing[name]) {
    log(`  ${id}: reusing existing ${name}.md`)
    return true
  }
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
  if (res === null) {
    log(`  ${id}: ${name} phase failed or was skipped — stopping this ticket`)
    return false
  }
  const p = await persistArtifact(id, name, phaseLabel)
  if (!p || !p.ok) {
    log(`  ${id}: ${name} reported done but no artifact was staged/persisted — ${p?.error ?? 'no result'} (stopping this ticket)`)
    return false
  }
  log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
  return true
}
```

— `.claude/workflows/qrspi-batch.js:512-532`

```javascript
    const a = r.decision.action
    log(`  ${t.id}: decision=${a} — ${r.decision.reason}`)
    let res
    switch (a) {
      case 'run_design': res = await doDesign(t, r); break
      case 'advance':
        res = r.decision.nextPhase === 'plan' ? await doPlan(t, r)
            : r.decision.nextPhase === 'implementation' ? await doImplementation(t, r)
            : skip(t, r.decision, `advance to unknown phase ${r.decision.nextPhase}`)
        break
      case 'submit': res = await doSubmit(t, r); break
      ...
    }
```

— `.claude/workflows/qrspi-batch.js:1641-1662`

**Dependencies:** Upstream: `phase()`/`log()`/`agent()` injected harness globals (no Node FS/`import` access — see Q12). Downstream: the typed `.claude/agents/qrspi-*` phase agents spawned via `agent({agentType})`. The JS shell cannot run Python/git directly — every mechanic is delegated to a worker agent shelling out to `scripts/*.py`.
**Implicit contracts:** Any event hook inserted in JS **cannot do file IO itself** (the Workflow sandbox has no FS — Q12, testing-dynamic-workflows.md:36-44). It must either (a) shell out to a Python event-writer via an `agent()` worker (matching the `persistArtifact`/resolve/restack pattern), or (b) the event writes must live in the Python scripts the workers already invoke. `runPhase` is the established "single success gate" pattern (testing-dynamic-workflows.md:255-264) — the same place a success/failure event belongs.

## Q2: How does the pipeline currently pass `ticket_id` and `phase` between stages, so the event-log writer can populate those fields without re-deriving them?

**Answer:** `ticket_id` is the ticket object `t.id` threaded through every function call (`doDesign(t, r)`, `runPhase(..., id, ...)`, etc.). `phase` is passed two ways: (1) a human `phaseLabel` string argument to `runPhase`/`agent({phase})` (e.g. `'Design'`, `'Plan'`); and (2) the **authoritative** machine phase on the resolver decision: `r.decision.phase` (active phase) and `r.decision.nextPhase` (target). The resolve envelope (`qrspi_resolve.py` `build_envelope`, lines 268-327) carries `decision` (with `phase`/`nextPhase`/`action`/`reason`), `worktreeDir`, `repoRoot`, `existing{}`, plus `ticket` is the input. The `stg(id, name)` helper (qrspi-batch.js:464) deterministically derives the staging path `/tmp/phase-stage/<id>/<name>.md` from `id` + artifact name — the same `(ticket, artifact)` tuple an event writer would key on.

**Evidence:**

```javascript
const stg = (id, name) => `/tmp/phase-stage/${id}/${name}.md`
```

— `.claude/workflows/qrspi-batch.js:464`

```python
    env = {
        "ok": ok,
        "repoRoot": REPO_ROOT if repo_root is None else repo_root,
        "worktreeDir": worktree_dir,
        "existing": existing,
        "decision": decision,
        ...
        "ticketContentPath": ticket_content_path,
```

— `scripts/qrspi_resolve.py:313-325` (envelope fields available to consumers)

**Dependencies:** `qrspi_resolve.py` produces the envelope; `parseResolveEnvelope` (qrspi-batch.js) consumes `ok`/`worktreeDir`/`decision.action` (testing-dynamic-workflows.md:155-156 — note: only those few fields are contract-pinned; `decision.phase`/`nextPhase`/`reason` are guarded only by the producer-side byte-match fixture).
**Implicit contracts:** `t.id` is the canonical ticket key (format `RUS-N`). The artifact set is fixed: `ARTIFACTS = ["questions","research","design","structure","plan","worktree"]` (qrspi_persist.py:52; same list in qrspi_resolve.py `detect_existing`). An event writer keying on `(t.id, decision.phase)` reuses already-passed values — no re-derivation needed. Phases (PR-gated) collapse to three PRs: design / plan / implementation (CLAUDE.md lifecycle).

## Q3: What existing mechanism writes files under `.qrspi/<id>/` (e.g. the staging-plus-move persist path), and does the same append target `.qrspi/observability/events.jsonl` live inside the worktree or the main checkout?

**Answer:** Two existing mechanisms write under `.qrspi/<id>/`:
1. **`scripts/qrspi_persist.py`** — the staging+move persist path for phase artifacts. The agent writes to a token-free staging path `/tmp/phase-stage/<id>/<artifact>.md`; this script moves it to the canonical `dest_path(repo_root, ticket, artifact)` = `<repo_root>/.worktrees/<id>/.qrspi/<id>/<artifact>.md` (qrspi_persist.py:67-72), verifying non-empty before+after (lines 74-92).
2. **`scripts/qrspi_metrics_append.py`** — the **direct precedent for a JSONL event writer.** It APPENDS one JSON line per call to `<repo_root>/.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl` via `append_line()` (qrspi_metrics_append.py:82-99), creating the parent dir, then verifying non-empty (fail-closed).

The destination lives in the **worktree** (`.worktrees/<id>/.qrspi/<id>/`), NOT the main checkout's `.qrspi/`. Both scripts resolve the **host checkout root** via `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` — git-common-dir first, so it yields the MAIN checkout root even when invoked from a worktree, then they join `.worktrees/<id>/.qrspi/<id>/` onto it (qrspi_metrics_append.py:60-64, qrspi_persist.py:67-72). Joining the worktree path onto a worktree-derived root would double-nest (`.worktrees/<id>/.worktrees/<id>/...`) — the exact bug `resolve_repo_root` exists to prevent (qrspi_metrics_append.py:20-28).

Note: there is **no `.qrspi/observability/` directory anywhere in the repo today** and no `events.jsonl` — the only `.jsonl` artifacts are `.qrspi/<id>/critic-metrics.jsonl` (5 found, all per-ticket, all under `.worktrees/<id>/.qrspi/<id>/`).

**Evidence:**

```python
def ledger_path(repo_root, ticket):
    """Canonical per-ticket ledger path. ..."""
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket,
                        "critic-metrics.jsonl")

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

— `scripts/qrspi_metrics_append.py:60-99`

**Dependencies:** Both depend on `qrspi_paths.resolve_repo_root` (the single source of truth for host-root resolution, qrspi_paths.py:111-143). The persist path is gated inside `runPhase`; the metrics-append path was driven by the now-removed critic loop (see Inconsistencies).
**Implicit contracts:** A `.qrspi/observability/events.jsonl` target keyed to ONE ticket would naturally live at `<root>/.worktrees/<id>/.qrspi/<id>/...` (per-ticket, mirroring critic-metrics.jsonl). A **shared cross-ticket** `.qrspi/observability/events.jsonl` (one global file) would be a NEW layout decision — it would live in the MAIN checkout `<root>/.qrspi/observability/` and is subject to the concurrency concern in Q8 (separate worktrees). The codebase has no precedent for a shared/global JSONL — every existing JSONL is per-ticket inside the worktree.

## Q4: What is the existing interface for reading flat configuration keys (e.g. `ciReviseCap`) from `.qrspi/config.json`, which the rotation-size, retention-days, and log-level settings would reuse?

**Answer:** There are TWO interfaces, and the `ciReviseCap` precedent uses the **second**, not the first:
1. **`scripts/qrspi_config.py` CLI** (`--key <name>`) — a self-locating helper that prints `{"ok":true,"key":...,"value":<str|null>}`. Its pure selector `select_value` returns `config[key]` when present *and truthy*, else a per-key default from `DEFAULTS` (only `linearProject="QRSPI"` registered; unknown keys default to `""`). It is **string-valued only** (project memory: "Config reader is single-top-level-key only"). Used by JS via `parseConfigEnvelope`.
2. **`qrspi_config.read_config(repo_root)`** — the underlying best-effort reader returning the raw parsed dict (`{}` on any OSError/ValueError, or if JSON is not a dict). **This is what `ciReviseCap` actually uses**: `qrspi_resolve.py:406-412` `load_ci_revise_cap` calls `read_config()` then `coerce_cap(config.get("ciReviseCap"))` — reading the raw dict directly, NOT through the string-only `--key` CLI, precisely because `ciReviseCap` is an integer.

So rotation-size (int), retention-days (int), and log-level (string enum) settings should follow the **`ciReviseCap` model**: read the raw dict via `qrspi_config.read_config()` and apply a per-key `coerce_*` pure function with a default fallback (the `coerce_cap` pattern, qrspi_resolve.py:394-403), NOT the `--key` CLI (which would coerce ints/strings incorrectly).

**Evidence:**

```python
def coerce_cap(value):
    """Coerce a config `ciReviseCap` value into a positive int, falling back to the
    documented default (3). Anything that is not a positive integer ... yields the default."""
    if isinstance(value, bool) or not isinstance(value, int):
        return CI_REVISE_CAP_DEFAULT
    return value if value > 0 else CI_REVISE_CAP_DEFAULT

def load_ci_revise_cap(repo_root=REPO_ROOT):
    config = qrspi_config.read_config(repo_root)
    return coerce_cap(config.get("ciReviseCap"))
```

— `scripts/qrspi_resolve.py:394-412`

```python
def select_value(config: dict, key: str, default: str) -> str:
    value = config.get(key)
    return value if value else default
```

— `scripts/qrspi_config.py:36-42` (string-valued `--key` path — NOT what ciReviseCap uses)

**Dependencies:** `qrspi_config.read_config` is imported by `qrspi_resolve.py` (and others) for raw-dict reads. `config.example.json` documents flat keys: `ciReviseCap`, `linearProject`, `linearTeam`, `reviewers`, `teamReviewers` are all top-level (config.example.json).
**Implicit contracts:** Flat top-level keys only — no dot-path nesting (project memory: "qrspi_config_reader_single_key_only"). `$comment`-prefixed keys are documentation, ignored by the harness (config.example.json:2). Defaults must be applied by the reader so an absent config file (the common case — `.qrspi/config.json` is gitignored) takes documented defaults. A `coerce_*` function must reject `bool` explicitly (it is an `int` subclass) — see qrspi_resolve.py:400-401.

## Q5: Do any current scripts expose a reusable logging or event-writing function, or does each script emit output ad hoc, determining whether a shared logging module must be introduced?

**Answer:** There is **no shared logging module.** The closest reusable primitives are:
- `qrspi_metrics_append.append_line(path, ledger_line)` (qrspi_metrics_append.py:82-99) — a reusable JSONL-append-with-verify function, but it lives in a CLI module (not a shared lib) and is coupled to the critic-metrics ledger path + envelope (`wrap_envelope` injects `ticketId`/`timestamp`/`runId`).
- `qrspi_paths.py` is the only true shared module (`engine_root`, `resolve_repo_root`); siblings `sys.path.insert(0, ENGINE_ROOT)` then `import qrspi_paths`.

Otherwise **each script emits ad hoc**: the dominant convention is a single JSON envelope `json.dump(env, sys.stdout, indent=2); print()` on stdout (used by qrspi_persist, qrspi_resolve, qrspi_metrics_append, qrspi_ci_revise_bump, qrspi_restack, qrspi_sync_trunk, qrspi_land_verify, qrspi_cleanup, qrspi_provision, qrspi_pr_body, qrspi_revise_amend, qrspi_clear_stale_pr, qrspi_critics_config, qrspi_critic_summary — 15 scripts). A few non-orchestration scripts (diagnose.py, meta_agent.py, eval_all.py, revise.py, qrspi_research_digest.py) write human text to `sys.stderr`.

**Conclusion:** A shared event-writing module would be **new infrastructure**, but it has a clean precedent to generalize: the `append_line` + `wrap_envelope` + `resolve_repo_root` + non-empty-verify + fail-closed pattern in `qrspi_metrics_append.py`. The cleanest shape is a new `scripts/qrspi_events.py` (pure helpers + CLI) mirroring `qrspi_metrics_append.py` with a `*_test.py` sibling, importing `qrspi_paths`.

**Evidence:**

```python
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)

import qrspi_paths  # noqa: E402
```

— `scripts/qrspi_metrics_append.py:52-55` (the sibling-import idiom every script repeats)

**Dependencies:** None centralized except `qrspi_paths`. The JS shell has no logging beyond the injected `log()` global (no file IO).
**Implicit contracts:** Output discipline — orchestration scripts print exactly ONE JSON envelope to stdout (worker agents echo it verbatim; the JS parses it). Any human/diagnostic text MUST go to stderr to avoid corrupting that stdout contract (Q13). A new shared event writer must preserve this: structured JSON to a file, NOT to the stdout envelope channel.

## Q6: How is the consecutive-retry / backoff state currently represented (e.g. the `CI-Revise-Attempt` head-commit trailer and the exponential-backoff policy referenced in the ticket), so retry-attempt events can record `error code` and `backoff duration` consistently?

**Answer:** Retry state is represented as a **git head-commit message trailer** `CI-Revise-Attempt: N`, NOT a file or DB. It is the shared serialization contract between writer and reader:
- **Reader (gather):** `qrspi_pr_state.ci_revise_attempt` parses the trailer; the gather forces it to `0` whenever the rollup is not `red` (read-side reset).
- **Writer (increment):** `scripts/qrspi_ci_revise_bump.py` is the SOLE authority for the +1 on the CI-failure path. Pure core `bump_ci_revise_trailer(message)` (lines 91-118) and `parse_ci_revise_attempt(message)` (lines 75-88): absent ⇒ prior=0, last-occurrence wins, exactly one trailer after bump. The regex contract is `^CI-Revise-Attempt:\s*(\d+)\s*$` MULTILINE (qrspi_ci_revise_bump.py:64), mirrored in `qrspi_pr_state._CI_REVISE_ATTEMPT_RE`.
- **Cap evaluation:** `qrspi_resolve_state.resolve(state, ci_revise_cap=3)` (lines 173-303) — when `attempt < ci_revise_cap` → `revise`; at/above → `wait` (park). The cap comes from `load_ci_revise_cap` (Q4).

**There is NO exponential-backoff policy in the codebase.** The only retry-bounding mechanism is the linear consecutive-red **counter + cap** (default 3). There is no `backoff duration`, no sleep, no exponential schedule anywhere. The "exponential-backoff policy referenced in the ticket" does **not exist today** — NOT FOUND (searched `backoff`, `exponential`, `sleep`, `retry.*delay` across `scripts/` and `.claude/`; only matches are the ci-revise *counter*, which is a cap, not a backoff). Likewise there is no `error code` field captured anywhere — failures surface as free-text strings in the `error` envelope key or the per-ticket `catch` `summary` (Q9). An events feature recording `error_code`/`backoff_duration` would be introducing NEW fields with no existing source.

**Evidence:**

```python
def parse_ci_revise_attempt(message):
    matches = _CI_REVISE_ATTEMPT_RE.findall(message or "")
    if not matches:
        return 0
    try:
        return int(matches[-1])
    except (TypeError, ValueError):
        return 0
```

— `scripts/qrspi_ci_revise_bump.py:75-88`

```python
        if attempt < ci_revise_cap:
            ... (revise)
        ... % (frontier, attempt, ci_revise_cap))  (wait — park at cap)
```

— `scripts/qrspi_resolve_state.py:292-303`

**Dependencies:** Writer `qrspi_ci_revise_bump.py` ↔ reader `qrspi_pr_state.py` (shared regex contract) ↔ decision `qrspi_resolve_state.py` (cap). The orchestrator `doRevise` (qrspi-batch.js ~1185-1194) invokes the bump deterministically per red branch.
**Implicit contracts:** The counter is consecutive-red only and has two resets (read-side in gather when not red; writer-side in `doRevise` non-CI amends → `CI-Revise-Attempt: 0`). The trailer is written by a distinct message-only `gt modify -m` AFTER the content amend (the content amender preserves the message verbatim). Any retry event must read the attempt from this trailer, not invent its own counter.

## Q7: How are `trace_id`, `span_id`, and `parent_span_id` analogues (if any) currently generated or correlated across a single ticket's run, given the constraint that the harness forbids `Date.now()`/`Math.random()` (the runId bug)?

**Answer:** **There are NO trace_id/span_id/parent_span_id analogues in the codebase today** (NOT FOUND — searched `trace_id`, `span_id`, `parent_span`, `trace`, `span` across `scripts/` and `.claude/workflows/`; zero hits in code, only the questions/research artifacts of other tickets). The only correlation key is the per-ticket `t.id` (e.g. `RUS-85`).

The closest analogue is **`runId`** — but it is currently **orphaned**: `scripts/qrspi_metrics_append.py` *requires* a `--run-id` flag and stamps it onto every appended line (lines 67-79, 111-114), but `qrspi-batch.js` **no longer generates a runId** (verified: zero occurrences of `runId`, `Date.now`, `Math.random`, `crypto.randomUUID` in the current qrspi-batch.js). The runId-bearing critic-metrics path was removed in the latest commit ("Remove all autonomous batch critics + research citation check", HEAD 1898b39). So the `--run-id` consumer exists with no live producer.

The **`Date.now()`/`Math.random()` prohibition is real and documented** (project memory: "qrspi-batch runId Date.now bug" — the runId fallback used forbidden `Date.now()`/`Math.random()`, which fails intermittently when `crypto.randomUUID` is absent in the sandbox). The sandbox lacks `process`, `require`, FS (testing-dynamic-workflows.md:209-224). The only blessed ID source was `crypto.randomUUID()` (when available). A new run-correlation id for events must NOT use `Date.now()`/`Math.random()`; the established safe approach was `crypto.randomUUID()`, or a deterministic id derived from inputs (e.g. ticket id + phase).

**Evidence:**

```python
def wrap_envelope(record, ticket, timestamp, run_id):
    line = dict(record)
    line["ticketId"] = ticket
    line["timestamp"] = timestamp
    line["runId"] = run_id
    return line
```

— `scripts/qrspi_metrics_append.py:67-79` (the only `runId` field in the codebase — orphaned consumer)

**Dependencies:** `qrspi_metrics_append.py --run-id` (orphaned). No JS producer remains.
**Implicit contracts:** Correlation today is purely by `ticketId`. A trace/span model is entirely greenfield. Hard constraint: no `Date.now()`/`Math.random()` in the JS shell (project memory). `timestamp` is generated Python-side as `datetime.now(timezone.utc).isoformat()` (qrspi_metrics_append.py:133) — the established, allowed timestamp source (Python, not JS).

## Q8: When two tickets run concurrently in separate worktrees, do their event writes target the same `.qrspi/observability/events.jsonl`, and what currently guarantees append atomicity for crash-safe, never-rewritten appends?

**Answer:** **Concurrent batch runs are NOT the current execution model** — within a single `qrspi-batch` run, tickets are processed **strictly sequentially** ("Sequential: tickets share one .git index, so worktree/Graphite ops must not race", qrspi-batch.js:1606; the main loop is a plain `for` over tickets, :1610). So there is no in-run concurrency.

However, *separate concurrent invocations* (two `claude` sessions / two batch runs) ARE possible per the CLAUDE.md worktree design ("multiple agents to work on different tickets concurrently"). Under the existing per-ticket JSONL layout, each ticket writes to its OWN file `<root>/.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl` — so two *different* tickets never target the same file (isolation by worktree). A **shared** `.qrspi/observability/events.jsonl` (one global file) would be a NEW design that DOES create a shared write target across worktrees.

**Atomicity guarantee today:** the only mechanism is POSIX append mode — `open(path, "a")` then a single `fh.write(json.dumps(line) + "\n")` (qrspi_metrics_append.py:88-90). There is **NO explicit locking, no `O_APPEND` flag set deliberately, no fsync, no atomic-rename.** A single `write()` of a short line under `"a"` is atomic on local filesystems up to `PIPE_BUF`/page boundaries, but this is implicit, not engineered. There is no crash-safety machinery beyond the post-write non-empty verify (lines 91-99). No existing JSONL is ever rewritten — they are append-only by construction (`"a"` mode, one line per call).

**Evidence:**

```javascript
// Sequential: tickets share one .git index, so worktree/Graphite ops must not race.
const results = []
...
for (let i = 0; i < tickets.length; i++) {
  const t = tickets[i]
```

— `.claude/workflows/qrspi-batch.js:1606-1611`

```python
    with open(path, "a") as fh:
        fh.write(json.dumps(ledger_line) + "\n")
```

— `scripts/qrspi_metrics_append.py:89-90` (the entire atomicity story: POSIX append, one write)

**Dependencies:** Worktree isolation is provided by `qrspi_paths.resolve_repo_root` (git-common-dir) + the per-ticket path join. `.worktrees/` is gitignored (.gitignore).
**Implicit contracts:** Per-ticket files = isolation-by-path (no contention). A shared global events file would break that isolation guarantee and would need explicit append-atomicity (e.g. `O_APPEND` open + single write per line, or file locking) that does NOT exist today. The append-only + non-empty-verify + fail-closed convention (never rewrite, never partial) is the established crash-safety posture.

## Q9: What is the current behavior when a phase worker crashes mid-transition — is there any existing failure-capture point where a `failure`/`retry` event could be emitted before the process exits?

**Answer:** Yes — there are exactly two failure-capture points, both in `qrspi-batch.js`:
1. **`runPhase` null sentinel** (qrspi-batch.js:518-528): when `agent()` returns `null` (the bare failure sentinel — the seam discards the error text, testing-dynamic-workflows.md:300-306) OR when `persistArtifact` returns `!ok`, `runPhase` logs and returns `false`, stopping that ticket's phase. This is a *clean* failure (no exception).
2. **The per-ticket `try/catch`** (qrspi-batch.js:1618-1675): wraps resolve + restack + the entire action dispatch. A *thrown* worker (e.g. a finalize worker whose StructuredOutput is lost to a transient API/socket error, even after side effects landed) is caught at lines 1671-1675, logged with `summary = err?.message ?? String(err)`, recorded as `{action:'errored', summary}`, and the loop **continues to the next ticket** (per-ticket isolation). The idempotent resolver reconciles partial work on re-run.

These are the natural emission points for `failure` events. **Critical constraint:** the JS sandbox has no FS, so the event emission at these points cannot be a direct file write — it must shell to a Python writer via `agent()`, OR (more robustly for crash-safety) the failure event must be emitted by the Python script itself before it exits non-zero (every script already has a fail-closed `ok:false` + non-zero-exit path — e.g. qrspi_persist.py:128-133, qrspi_metrics_append.py:116-129). A worker process that *crashes* (vs. returns null) gives the JS only a bare `null` with no error detail — so the richest failure data lives Python-side, before the script returns.

There is **no `retry` concept at the phase level** — phases recompute on re-run (resume guarantee, testing-dynamic-workflows.md:230-264), they do not retry in-process. The only retry construct is the CI-revise loop (Q6), bounded by the cap.

**Evidence:**

```javascript
  } catch (err) {
    const summary = err?.message ?? String(err)
    log(`  ${t.id}: ERRORED — ${summary} (side effects may have partially landed; resolver reconciles on re-run)`)
    results.push({ ticketId: t.id, action: 'errored', summary })
  }
```

— `.claude/workflows/qrspi-batch.js:1671-1675`

**Dependencies:** `agent()` seam (returns `null` on transient fault, error text discarded — testing-dynamic-workflows.md:289-311). `persistArtifact` → `qrspi_persist.py`.
**Implicit contracts:** A mid-unit interruption recomputes, never corrupts (post-validation persist gate, testing-dynamic-workflows.md:253-264). `agent()` failure is unobservable beyond `null` — a JS-side failure event can record only "phase X for ticket Y failed", not why. For rich failure detail (error message), emit the event from the Python worker before its non-zero exit. No transient-retry classifier exists or is buildable at the `agent()` seam (testing-dynamic-workflows.md:288-311).

## Q10: How does the pipeline behave today when `.qrspi/config.json` is absent or a setting is malformed (e.g. non-integer), and what fallback would the rotation-size (default 10 MB), retention (default 30 days), and log-level (default?) settings need to mirror?

**Answer:** Behavior is **best-effort with silent default fallback, never raising**:
- **Absent file / unreadable / malformed JSON / non-dict JSON:** `qrspi_config.read_config` catches `(OSError, ValueError)` and returns `{}` (qrspi_config.py:51-56); a non-dict top-level (e.g. a JSON array) also returns `{}` (line 54). Tests confirm: `test_missing_file_returns_empty`, `test_malformed_json_returns_empty`, `test_non_dict_json_returns_empty` (qrspi_config_test.py:58-72).
- **Malformed value (e.g. non-integer `ciReviseCap`):** the per-key `coerce_cap` rejects anything that is not a positive int — `None`, non-positive, `bool`, `float`, `str` all → default 3 (qrspi_resolve.py:394-403). `bool` is rejected explicitly (it is an int subclass).
- **String `--key` path:** `select_value` returns the default when the key is absent OR falsy/empty (qrspi_config.py:36-42).

So the **fallback pattern to mirror** is: read the raw dict best-effort (`read_config`), then apply a dedicated pure `coerce_<setting>(value)` per setting that returns the documented default for ANY invalid value. Rotation-size (default 10 MB → presumably `10 * 1024 * 1024` bytes, must reject non-positive/non-int/bool like `coerce_cap`), retention-days (default 30, same integer coercion), and log-level (string enum — **default NOT specified in the codebase; NOT FOUND** — would need a `coerce_log_level` validating against an allowed set, defaulting to e.g. `"info"`, but there is no existing log-level constant to mirror; the only existing string-default is `linearProject="QRSPI"`).

**Evidence:**

```python
def read_config(repo_root: Path) -> dict:
    path = Path(repo_root) / ".qrspi" / "config.json"
    try:
        with open(path) as fh:
            cfg = json.load(fh)
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}
```

— `scripts/qrspi_config.py:45-56`

**Dependencies:** `read_config` is the shared best-effort reader; `coerce_cap` is the per-key validation precedent.
**Implicit contracts:** Config is always optional (`.qrspi/config.json` is gitignored — .gitignore). NO setting may raise on absence/malformation — fail to the documented default. Each typed setting needs its own pure `coerce_*` (unit-tested) because `read_config` returns raw JSON types untouched. `bool` must be rejected explicitly for integer settings.

## Q11: What is the existing unit-test convention and runner that new event-log, schema-validation, and rotation tests must conform to?

**Answer:** Convention: **stdlib-only `unittest`, one `scripts/<name>_test.py` sibling per script, runnable standalone** (`python3 scripts/<name>_test.py`, exit 0 on success). The aggregating runner is `scripts/run_tests.py` — it discovers every `scripts/*_test.py`, runs each as its OWN subprocess (`run_one`, line 51-75), prints PASS/FAIL, and exits non-zero if any fail (`run_suite`/`main`, lines 78-138). Filter with a substring arg (`python3 scripts/run_tests.py events`); enumerate with `--list`; per-file timeout 180s. The same command is the CI regression gate (`.github/workflows/tests.yml`, CLAUDE.md). Test structure: `class XTest(unittest.TestCase)` with `test_*` methods, `tempfile.TemporaryDirectory()` for FS tests (see qrspi_metrics_append_test.py:7,67 — the closest template: `LedgerPathTest`, `WrapEnvelopeTest`, `AppendCliTest` covering path/no-double-nesting, envelope, fail-closed-on-invalid-JSON, round-trip).

**Evidence:**

```python
def discover_tests(scripts_dir=SCRIPT_DIR, pattern=None):
    names = sorted(
        n for n in os.listdir(scripts_dir)
        if n.endswith("_test.py")
    )
    if pattern:
        names = [n for n in names if pattern in n]
    return [os.path.join(scripts_dir, n) for n in names]
```

— `scripts/run_tests.py:36-48`

```python
class AppendCliTest(unittest.TestCase):
    ...
    def test_first_call_creates_single_line_ledger(self):
    def test_invalid_json_record_fails_closed_and_writes_nothing(self):
    def test_path_resolution_no_double_nesting(self):
```

— `scripts/qrspi_metrics_append_test.py:65,85,130,142` (template for an event-writer test)

**Dependencies:** `run_tests.py` (auto-discovery — zero registration needed for a new `*_test.py`). CI: `.github/workflows/tests.yml`.
**Implicit contracts:** Stdlib only (no pytest — requirements.txt is minimal). A new test file is picked up automatically by name suffix `_test.py`. Tests must exit non-zero on failure (each ends with `unittest.main()` under `if __name__ == "__main__"`). Pure helpers are tested directly; subprocess/CLI behavior is tested via temp dirs. Rotation tests would create a temp file, write past the size threshold, assert the rotation occurred (no existing rotation precedent — greenfield).

## Q12: For JS code in `.claude/workflows/qrspi-batch.js` that is described as harness-coupled and not unit-testable in isolation, how is its behavior currently verified, so event-emission added there can be covered?

**Answer:** `qrspi-batch.js` is verified four ways (testing-dynamic-workflows.md):
1. **Logic-out-of-JS convention (primary):** any new deterministic decision goes into a `scripts/*.py` helper with a `_test.py` sibling, NOT inline JS (md:109-114). So **event-emission logic belongs in Python** (a `qrspi_events.py`), and the JS only shells to it — the JS seam stays logic-free and the coverage lands in the tested Python core.
2. **`node:vm` contract-seam consumer tests:** `scripts/qrspi_contract_fixtures_consumer_test.py` drives `scripts/contract_seam_runner.js`, which loads `qrspi-batch.js` via a strip-`export` + async-wrap + injected-globals recipe and exposes the `parse*` parsers through an appended shim, asserting each against committed fixtures (md:138-161). This covers all 8 `parse*` envelope parsers.
3. **Producer-side contract tests:** `scripts/qrspi_contract_fixtures_producer_test.py` asserts each Python producer's output matches the same `scripts/fixtures/contract_seam/<seam>/<variant>.json` goldens byte-for-byte (md:135-137).
4. **Syntax gate** (`scripts/check_workflows.js` / `check_workflows_test.py`): validates the workflow parses the way the harness loads it (md:116-122).

**The JS is NOT unit-testable as a whole** (top-level `return`/`await`, injected globals `agent`/`parallel`/`phase`/`log`/`args`, no `import`/`require`/FS — md:29-44, 209-224). So any **event emission added in the JS shell** can only be covered by (a) pushing the emission into a Python script and unit-testing that, plus (b) if a NEW JS parser is added for an event-writer envelope, adding a fixture pair under `scripts/fixtures/contract_seam/<new-seam>/` and extending both contract tests. There is no way to assert the JS *calls* the emitter (the `agent()` seams are eval territory, not unit-test — md:184-202).

**Evidence:**

```
- Top-level `return` (last line) and top-level `await` throughout the driver.
- References harness-injected globals that do not exist in plain Node:
  `agent()`, `parallel()`, `pipeline()`, `phase()`, `log()`, `args`, `budget`, ...
- The Workflow runtime exposes no filesystem / Node.js API access, so the
  script cannot `import`/`require` a sibling helper module.
```

— `docs/testing-dynamic-workflows.md:33-40`

**Dependencies:** `scripts/contract_seam_runner.js` (node:vm harness), the two `qrspi_contract_fixtures_*_test.py`, `scripts/fixtures/contract_seam/`. All auto-discovered by `run_tests.py`.
**Implicit contracts:** The contract guard is "as strong as the fixtures are complete" — each parser validates only the fields it dereferences; other envelope fields are pinned only by the producer-side byte-match (md:153-161). To cover an event-writer envelope's JS parse, add a `wellformed.json` + malformed variant and extend the consumer/producer tests. The JS-calls-emitter causation remains inspection-only (md:273-286).

## Q13: What output channels do qrspi CLI commands currently write to (stdout, stderr, files), so structured JSON logging to a file with optional stderr for interactive use can be layered without breaking existing parsing?

**Answer:** Strict channel discipline exists and MUST be preserved:
- **stdout = the machine contract.** Every orchestration script prints exactly ONE JSON envelope to stdout: `json.dump(env, sys.stdout, indent=2); print()` (15 scripts — qrspi_persist, qrspi_resolve, qrspi_metrics_append, qrspi_ci_revise_bump, qrspi_restack, qrspi_sync_trunk, qrspi_land_verify, qrspi_cleanup, qrspi_provision, qrspi_pr_body, qrspi_revise_amend, qrspi_clear_stale_pr, qrspi_critics_config, qrspi_critic_summary; qrspi_config uses `print(json.dumps(...))`). The worker agent echoes this verbatim; `qrspi-batch.js` `parse*` functions `JSON.parse` it. **Any non-JSON byte on stdout corrupts this** (the resolve worker is explicitly told to output the JSON "exactly and verbatim, with NO surrounding prose, NO code fences" — qrspi-batch.js:594-598).
- **stderr = human/diagnostic text.** Used by non-orchestration scripts (diagnose.py, meta_agent.py, eval_all.py, revise.py, qrspi_research_digest.py) and `run_tests.py` error output (`file=sys.stderr`, run_tests.py:134).
- **files = artifacts/ledgers.** `.worktrees/<id>/.qrspi/<id>/*.md` (persist) and `*.jsonl` (metrics-append).

So "structured JSON logging to a file with optional stderr for interactive use" fits cleanly: **write events to a file** (the jsonl precedent), and if any interactive echo is wanted, send it to **stderr** — NEVER stdout, which is reserved for the single-envelope contract.

**Evidence:**

```python
    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if error is None else 1
```

— `scripts/qrspi_persist.py:131-133` (the stdout-envelope contract every script honors)

**Dependencies:** JS `parse*` consumers depend on stdout being pure JSON. `run_tests.py` writes failures to stderr.
**Implicit contracts:** stdout is sacred (single JSON envelope); diagnostics go to stderr; durable data goes to files. The JS shell has no stdout/stderr/file access of its own — it only reads the worker's echoed stdout. An event writer adding stderr output must guard it so it never leaks into a script whose stdout is being parsed as the envelope (i.e. emit to a *separate* invocation/file, or strictly to stderr).

## Q14: Is there any existing log file, trace, or event artifact under `.qrspi/` today, and how is `.qrspi/observability/` (and the gitignore status of generated logs) currently treated?

**Answer:**
- **Existing event/ledger artifacts under `.qrspi/`:** YES — `.qrspi/<id>/critic-metrics.jsonl` (5 present: RUS-78, RUS-81, RUS-82, RUS-83, RUS-88), each a per-ticket append-only JSONL written by `qrspi_metrics_append.py`. These are the only `.jsonl` files in the repo. There are also per-ticket `.md` artifacts (questions/research/design/structure/plan/worktree, plus pr-summary.md, impl-log.md).
- **`.qrspi/observability/`:** does **NOT exist** (NOT FOUND — `find -type d -name observability` returns nothing). No `events.jsonl`, no trace files anywhere.
- **gitignore status:** `.qrspi/critic-metrics.jsonl` files are **NOT gitignored** — `git check-ignore` reports them as trackable/committable. The `.gitignore` ignores only: `.devcontainer`, `__pycache__`, `.worktrees/`, `.claude/scheduled_tasks.lock`, `.qrspi/config.json`, `.qrspi/features/`, `.env`. So generated `.qrspi/<id>/*` artifacts are NOT ignored by default and CAN be committed (consistent with the PR-gated model where design/plan artifacts are committed into the stack). Note the apparent tension: `.worktrees/` IS gitignored, yet artifacts are written to `.worktrees/<id>/.qrspi/<id>/` — within a worktree those paths are tracked relative to the worktree's own branch (the worktree is a separate checkout), not the main checkout's ignored `.worktrees/` view.

**A new `.qrspi/observability/events.jsonl` would need an explicit gitignore decision:** the critic-metrics precedent (committed, per-ticket, inside the worktree) suggests events could follow the same (committed) treatment; a *generated log* the ticket may want ephemeral would need an added `.gitignore` entry (e.g. `.qrspi/observability/` or `*.events.jsonl`) — there is no existing pattern for ignoring generated logs under `.qrspi/`.

**Evidence:**

```
.devcontainer
__pycache__
.worktrees/
.claude/scheduled_tasks.lock
# Local config override (per-user); see .qrspi/config.example.json
.qrspi/config.json
# Local /qrspi-feature elicitation scratch (per-user, pre-ticket)
.qrspi/features/
# Local API key file (per-user); parsed by scripts/grade.py load_api_key()
.env
```

— `.gitignore:1-9`

**Dependencies:** `qrspi_metrics_append.py` (the JSONL producer); `.gitignore`.
**Implicit contracts:** `.qrspi/<id>/` artifacts are committable by default (only config.json / features/ are ignored). `.jsonl` ledgers are per-ticket, append-only, inside the worktree. There is no `observability/` namespace yet — introducing it is greenfield, and its gitignore treatment is an open decision (committed-like-critic-metrics vs ignored-as-generated-log).

---

## Discovered Patterns

- **"Self-locating Python helper, JS shells out, worker echoes stdout JSON verbatim" is the universal idiom.** Every deterministic mechanic is a `scripts/qrspi_*.py` that (1) derives the host root via `qrspi_paths.resolve_repo_root` (git-common-dir first, so it is the MAIN checkout even from a worktree), (2) does its work, (3) prints ONE JSON envelope `{ok, ..., error?}` to stdout, (4) exits 0/1. The JS spawns a worker agent that runs the command verbatim and echoes stdout, which a JS `parse*Envelope` consumes. `qrspi_metrics_append.py` is the closest template for a new event writer.
- **Fail-closed + non-empty-verify on every write.** `qrspi_persist.py` and `qrspi_metrics_append.py` both verify the destination is non-empty after writing and return `ok:false` on any failure; no retry, no silent partial. A new event writer must mirror this.
- **Pure-core / imperative-shell split is enforced as policy** (testing-dynamic-workflows.md:109-114): decision logic lives in unit-tested Python; the JS shell is logic-free glue. New event logic belongs in Python.
- **Per-ticket isolation everywhere:** path keying by `t.id`, worktree-scoped writes, sequential processing within a run, per-ticket `try/catch`. There is no shared cross-ticket state file.
- **Config is optional + best-effort + per-key coercion.** `read_config` returns `{}` on any error; each typed setting has its own pure `coerce_*` rejecting bad values to a documented default. `bool` is rejected explicitly for integer settings.
- **stdout is reserved for the single JSON envelope; stderr for human text; files for durable data.** Violating the stdout contract corrupts the worker→JS parse.

## Inconsistencies

- **Orphaned `runId` consumer (live mismatch):** `scripts/qrspi_metrics_append.py` *requires* `--run-id` and stamps `runId` on every line, but the current `qrspi-batch.js` generates NO runId (the runId-bearing autonomous critic-metrics path was removed in HEAD commit 1898b39 "Remove all autonomous batch critics"). The consumer exists with no live producer. Any new event feature that wants run correlation cannot reuse a live runId source — it must create one (and avoid `Date.now()`/`Math.random()`, project-memory runId bug).
- **Ticket references a non-existent "exponential-backoff policy" and "error code":** the codebase has only a linear consecutive-red counter + cap (`CI-Revise-Attempt` trailer, default cap 3) — NO exponential backoff, NO sleep/delay, NO `error_code` field anywhere. Events recording `backoff_duration`/`error_code` would introduce fields with no existing source (Q6).
- **Ticket references `.qrspi/observability/events.jsonl` which does not exist:** there is no `observability/` directory and no shared/global events file. Every existing JSONL is per-ticket (`.qrspi/<id>/critic-metrics.jsonl`) inside the worktree. A shared global events file is a NEW layout that breaks the per-ticket isolation pattern and would need explicit append-atomicity + a gitignore decision (Q3, Q8, Q14).
- **Two config-read interfaces with different type semantics:** the `qrspi_config.py --key` CLI is string-only (`select_value` returns the value or a string default), while `ciReviseCap` deliberately bypasses it and reads the raw dict via `read_config()` + `coerce_cap` to get an int. A naive reuse of `--key` for integer settings (rotation-size, retention-days) would be wrong — they must follow the `read_config` + `coerce_*` path (Q4).
- **`.worktrees/` is gitignored in the main checkout, yet artifacts (including committable `.qrspi/<id>/*.md` and `.jsonl`) are written there.** This is intentional (worktrees are separate checkouts on their own branches) but is a frequent source of confusion about whether a generated artifact is tracked — relevant to deciding the gitignore treatment of a new events log (Q14).
- **The `agent()` failure seam discards error detail (only `null`):** failure events emitted from the JS shell can record *that* a phase failed but not *why*; rich failure detail (error message, code) is only available Python-side before a script's non-zero exit (Q9). This caps how informative a JS-emitted failure event can be.
