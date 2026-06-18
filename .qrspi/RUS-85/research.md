# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

---

## Q1: Where in the pipeline do phase transitions (phase start, phase end, success, failure, retry) currently occur, and at which call sites would event-emission hooks need to attach to capture every transition?

**Answer:** Phase orchestration lives entirely in `.claude/workflows/qrspi-batch.js`. There is **no event-emission layer today** — phase boundaries are marked only by two injected global functions, `phase(<name>)` and `log(<string>)`, which are NOT defined in the file (they are provided by the Workflow runner host; grep finds no `const phase`/`function phase`/`const log` definition). They are side-effecting console markers, not structured events.

The canonical transition points an emitter would attach to:

1. **Top-level phase markers** — `phase('Query')` (qrspi-batch.js:2467), `phase('Sync')` (:2649), and per-ticket `phase('Resolve')` (:1382), `phase('Restack')` (:2682), `phase('Design')` (:1529 in `doDesign`), `phase('Plan')` (:1650), `phase('Finalize')` (:1607, :1674, :1968, etc.). These fire as a step *starts*.
2. **The per-artifact phase runner `runPhase(name, agentType, prompt, existing, id, phaseLabel, criticConfig)`** (qrspi-batch.js:1305) — the single chokepoint every Questions/Research/Design/Structure/Plan/Worktree artifact passes through. It already has clean start/success/failure forks:
   - reuse/start: `log("  ${id}: reusing existing ${name}.md")` (:1307)
   - producer success → critic/node-check → persist gate (:1369–1375)
   - every failure path returns `false` with a `log(...)` (:1312, :1339, :1353, :1371)
3. **The main dispatch `switch (a)`** in the per-ticket loop (qrspi-batch.js:2693–2711) — maps `decision.action` ∈ `run_design | advance | submit | reset | revise | land | wait | entry_blocked` to a handler. The per-ticket `try/catch` (:2667–2724) is where ticket-level success (`results.push(res)`, :2712) and failure (`action: 'errored'`, :2723) are recorded — the natural success/failure transition sink.
4. **Each worker `agent(prompt, {label, phase, ...})` call** — every spawn carries a `label` (e.g. `` `${name}:${id}` ``) and a `phase` string already, which is exactly the (phase, actor) tuple an emitter needs.

**Retry transitions** are NOT a uniform pipeline concept (see Q7): the only loop-with-cap is the CI-revise path; worker-level "retry once" is prose inside individual prompts.

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
```

— `.claude/workflows/qrspi-batch.js:1305-1314`

```js
    const a = r.decision.action
    log(`  ${t.id}: decision=${a} — ${r.decision.reason}`)
    let res
    switch (a) {
      case 'run_design': res = await doDesign(t, r); break
      case 'advance': ...
      case 'revise': res = await doRevise(t, r); break
      case 'land': res = await doLand(t, r); break
      ...
    }
    results.push(res)
```

— `.claude/workflows/qrspi-batch.js:2690-2712`

**Dependencies:** Upstream of every transition is `resolveTicket(t)` → `parseResolveEnvelope` (the decision); downstream is the typed `agent()`/`parallel()` host primitives. `phase`/`log` are runner-injected globals. The python resolver `scripts/qrspi_resolve.py` supplies the decision but emits no events.
**Implicit contracts:** `phase()`/`log()` are fire-and-forget (no return consumed). Workflow scripts FORBID `Date.now()`/`Math.random()` (they break resume — see runId, qrspi-batch.js:130-141); any timestamp/id generation in an emitter must use `crypto.randomUUID`/`crypto.getRandomValues` or an injected value, never a clock. The JS sandbox **cannot run python or shell directly** — every disk/subprocess side effect is delegated to a spawned `agent()` worker that runs ONE verbatim command. An event writer would have to follow that same delegate-to-worker pattern (as `persistArtifact`/`recordCriticMetrics` do).

---

## Q2: How is the per-phase success/failure outcome currently propagated back to the orchestrator (return value, exit code, exception), so an event emitter can read the authoritative status of each transition?

**Answer:** Three layered mechanisms, all already converging on the orchestrator:

1. **Python helper layer** — every `scripts/qrspi_*.py` prints a single JSON envelope to **stdout** carrying an `ok: bool` (and on failure an `error` string) AND mirrors it in the **process exit code** (`return 0 if ok else 1`). Examples: `qrspi_persist.py` `{ ok, repoRoot, src, dest, bytes, error? }` (qrspi_persist.py:121-133), `qrspi_resolve.py` emits the full decision envelope (:575-576), `qrspi_ci_revise_bump.py` `{ ok, branch, prior, new, error? }` (:226-229), `qrspi_metrics_append.py` `{ ok, ledger, lines, bytes, error? }` (:137-149). The CONTRACT throughout: read `ok` off **stdout**, not the exit code alone (stated repeatedly, e.g. qrspi-batch.js:2153).

2. **Worker→orchestrator layer** — a spawned `agent()` returns the worker's text or a schema'd object. The orchestrator re-parses it with a dedicated validator: `parseResolveEnvelope` (qrspi-batch.js:259), `parseRestackEnvelope` (:316), `parseCleanupEnvelope` (:351), `parseLandVerdict` (:365), `parseConfigEnvelope` (:381). A `null` worker result or a garbled echo becomes a clean `{ ok: false, error }` — **never a thrown exception**.

3. **Resolver decision layer** — `scripts/qrspi_resolve_state.py` is a PURE function: it does NO I/O, takes gathered PR state in, returns the `decision { action, phase, reason, ... }` object the orchestrator switches on (qrspi_resolve_state.py:7-9). Success/failure of a *phase* is not its concern; it computes the NEXT action.

In `runPhase`, the authoritative per-phase status is the **boolean return** (`true` = persisted, `false` = stopped) — driven by the persist gate (`persistArtifact` → `p.ok`, qrspi-batch.js:1369-1373). `doDesign`/`doPlan` map a `false` to `failTicket(t)` (:1544). Ticket-level outcome is the `res` object pushed to `results[]`, with `action: 'errored'` reserved for a thrown exception caught at :2720.

**Evidence:**

```js
  const p = await persistArtifact(id, name, phaseLabel)
  if (!p || !p.ok) {
    log(`  ${id}: ${name} reported done but no artifact was staged/persisted — ${p?.error ?? 'no result'} (stopping this ticket)`)
    return false
  }
  log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
  return true
```

— `.claude/workflows/qrspi-batch.js:1369-1375`

```python
    env = { "ok": error is None, "repoRoot": repo_root, "src": src, "dest": dest, "bytes": bytes_written }
    if error is not None:
        env["error"] = error
    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if error is None else 1
```

— `scripts/qrspi_persist.py:121-133`

**Dependencies:** `runPhase` ← `persistArtifact` ← `qrspi_persist.py`; dispatch loop ← `resolveTicket` ← `parseResolveEnvelope` ← `qrspi_resolve.py` (which internally calls `qrspi_pr_state.py` gather + `qrspi_resolve_state.py` decision).
**Implicit contracts:** The dual signal (stdout `ok` + exit code) is the universal status contract — an emitter reading "did this transition succeed" should read the parsed envelope's `ok`, mirroring the orchestrator. Per-ticket isolation: a thrown phase agent must NOT abort sibling tickets (the `try/catch` at :2667; comment :2663-2666). The resolver is **idempotent** — partial work is reconciled on re-run, so events must tolerate at-least-once re-emission of the same transition.

---

## Q3: What identifiers (ticket ID, phase, actor) are already available at each phase-transition point, and which of the schema fields (`trace_id`, `span_id`, `parent_span_id`) have no existing source and would need to be generated?

**Answer:**
**Already available at every transition:**
- **Ticket ID** — `t.id` (e.g. `RUS-8`), threaded through every handler (`doDesign(t,r)`, `runPhase(..., id, ...)`, every worker prompt). Validated shape `RUS-\d+` (TICKET_ARG normalization at qrspi-batch.js:183-185).
- **Phase** — every `agent()` call passes `{ phase: <string> }` (`'Query' | 'Resolve' | 'Restack' | 'Design' | 'Plan' | 'Implementation' | 'Finalize' | 'Critic' | 'Sync'`) and `runPhase` carries `phaseLabel`. The resolver's own phase vocabulary is `design | plan | implementation` (qrspi_resolve_state.py:61).
- **Actor / step label** — every `agent()` carries a `label` like `` `resolve:${t.id}` ``, `` `persist:${id}:${name}` ``, `` `revise:${t.id}` ``, `` `ci-revise-bump:${t.id}:${branch}` `` — a unique per-spawn identifier.
- **Run id** — `runId` is computed ONCE per invocation (qrspi-batch.js:133-141): `process.env.QRSPI_RUN_ID` else `crypto.randomUUID()` else a `crypto.getRandomValues` hex id else `'run-fallback'`. It is ALREADY stamped onto every appended metrics ledger line (passed as `--run-id` at :995). This is the closest existing analog to a `trace_id`.
- **Decision / action** — `r.decision.action` and `r.decision.reason` (logged at :2691).

**Would need to be generated (no existing source):**
- **`trace_id`** — no per-ticket-run trace id exists. `runId` is per-INVOCATION (covers ALL tickets in one batch), so it is too coarse to be a per-ticket trace id; a per-ticket trace id (e.g. `${runId}:${t.id}` or a fresh UUID per ticket) would need generating.
- **`span_id`** — none exists. Each `agent()` `label` is a human string, not a span id; a span id per transition must be generated.
- **`parent_span_id`** — none exists. The call graph (`doDesign` → `runPhase` → `persistArtifact` → worker) is implicit in JS control flow; no span hierarchy is materialized. A parent-span linkage must be threaded manually through the call chain.

**Evidence:**

```js
const runId =
  (typeof process !== 'undefined' && process.env && process.env.QRSPI_RUN_ID) ||
  (typeof crypto !== 'undefined' && crypto.randomUUID && crypto.randomUUID()) ||
  (typeof crypto !== 'undefined' && crypto.getRandomValues &&
    `run-${Array.from(crypto.getRandomValues(new Uint8Array(8)))
      .map((b) => b.toString(16).padStart(2, '0')).join('')}`) ||
  'run-fallback'
```

— `.claude/workflows/qrspi-batch.js:133-141`

```js
    { label: `revise:${t.id}`, phase: 'Finalize', schema: WORKER_SCHEMA }
```

— `.claude/workflows/qrspi-batch.js:2058` (representative of the label/phase tuple on every spawn)

**Dependencies:** `runId` is consumed downstream by `qrspi_metrics_append.py --run-id` and scoped by `scripts/qrspi_critic_summary.py` (per the comment at :126-132).
**Implicit contracts:** Any generated id MUST avoid `Date.now()`/`Math.random()` (resume-safety, :132). `runId` is the established "always present, always a string" field — a trace schema should reuse it (e.g. as the trace root) rather than invent a parallel id, to keep the metrics ledger and the new event log correlatable.

---

## Q4: What is the existing convention for writing to disk under `.qrspi/` (which helper, which path-resolution mechanism), and does a writer for the new `.qrspi/observability/events.jsonl` path fit that convention?

**Answer:** There is a strong, uniform convention, and an **append-only JSONL writer already exists** as a near-exact template.

**Path resolution:** All disk writes resolve the HOST checkout root through the single source of truth `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` (`scripts/qrspi_paths.py:111`). Precedence: explicit `--repo-root` → `git rev-parse --git-common-dir` (the MAIN checkout even from a worktree) → `__file__` parent. This deliberately yields the MAIN checkout, never a worktree, to avoid double-nesting (`qrspi_metrics_append.py:16-28`). `validate=False` keeps `gh` off the import path.

**Writer helpers:** Two relevant patterns —
- `scripts/qrspi_persist.py` — staging + deterministic MOVE (one-shot artifact persist). Computes the canonical `.worktrees/<id>/.qrspi/<id>/<artifact>.md` dest, verifies non-empty, fails closed.
- `scripts/qrspi_metrics_append.py` — **APPEND-only JSONL ledger** at `.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl` (`ledger_path`, :60-64). `append_line` opens with mode `"a"`, writes `json.dumps(line) + "\n"`, re-verifies non-empty, returns `(lines, bytes, error)` (:82-99). This is the **direct precedent** for `events.jsonl`.

**Fit assessment:** A `.qrspi/observability/events.jsonl` writer fits the convention with ONE notable difference — every existing `.qrspi/` path is **per-ticket and inside the worktree** (`.worktrees/<id>/.qrspi/<id>/...`). The proposed `.qrspi/observability/events.jsonl` (no `<id>` segment) implies a **single shared, repo-level** path. That is NOT how any current writer is shaped: `ledger_path`/`dest_path` always embed `<ticket>` twice and live under `.worktrees/<id>/`. A repo-root `.qrspi/observability/` would be a NEW path shape (and raises the concurrency concern in Q9 — a single shared file across parallel tickets, vs the per-ticket isolation every existing ledger enjoys). The qrspi token would still be model-corruptible, so the path must be computed by a self-locating script (never typed by a worker), exactly as `qrspi_persist`/`qrspi_metrics_append` do.

**Evidence:**

```python
def ledger_path(repo_root, ticket):
    """Canonical per-ticket ledger path. Pure..."""
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
```

— `scripts/qrspi_metrics_append.py:60-94`

**Dependencies:** Every writer imports the sibling `qrspi_paths` after `sys.path.insert(0, ENGINE_ROOT)` (qrspi_metrics_append.py:48-55). The JS side reaches them via `engineCmd(rel)` / `engineCmdFor(r, rel)` worker prompts (qrspi-batch.js:76, 105).
**Implicit contracts:** (1) repo root is computed by the script, never passed by a model; (2) parent dir is created with `makedirs(..., exist_ok=True)`; (3) the write is verified non-empty and fails CLOSED on any OSError; (4) output is a single JSON envelope on stdout with `ok` + exit code. A new event writer must honor all four.

---

## Q5: How do existing scripts (e.g. `scripts/qrspi_config.py`) read configuration keys, and what shape would the new configurable values (log level, rotation size, retention days) take given the reader supports only single top-level keys?

**Answer:** `scripts/qrspi_config.py` reads **exactly ONE top-level key** per invocation. `read_config(repo_root)` best-effort-parses `<root>/.qrspi/config.json` into a dict (returns `{}` on any OSError/ValueError, never raises — qrspi_config.py:45-56); `select_value(config, key, default)` returns `config[key]` when present-and-truthy, else the default (:36-42). The CLI is `python3 scripts/qrspi_config.py --key <name>` and prints `{ "ok": true, "key": "<name>", "value": <str|null> }` (:59-75). Per-key defaults live in a `DEFAULTS` dict (`{"linearProject": "QRSPI"}`, :33); unknown keys default to `""`.

**Critical constraint (confirmed):** the reader does **NOT** support dot-paths or nested objects. `select_value` only does `config.get(key)`. The JS-side `parseConfigEnvelope` further REJECTS any non-string value (`typeof env.value !== 'string'` → ok:false, qrspi-batch.js:389). So `qrspi_config.py` can read **only flat, top-level, string-valued keys**.

**Implication for new values:** `logLevel`, `rotationSize`, `retentionDays` CANNOT be read as a nested `observability: { ... }` block through `qrspi_config.py` + `parseConfigEnvelope` — that path returns strings only and reads single keys. Two precedents bracket the choice:
- **Flat top-level keys** (like `ciReviseCap`, the existing flat int knob — config.example.json:33) read via `qrspi_config.py --key <name>`. BUT `ciReviseCap` is an integer and is NOT actually read through `qrspi_config.py`/`parseConfigEnvelope` (which would reject the non-string); it is parsed elsewhere. So a flat key here would need either string-typed config values (`"logLevel": "info"`) or a NEW dedicated reader.
- **Nested block via a dedicated tested resolver** (like `critics: {...}` read by `scripts/qrspi_critics_config.py`, which reads `.qrspi/config.json` ONCE and emits the resolved `{ ok, phases, warnings }` — qrspi-batch.js:403-412). This is the established pattern for STRUCTURED multi-value config and is the natural fit for an `observability` block carrying level/size/retention with type coercion + defaults.

**Evidence:**

```python
def select_value(config: dict, key: str, default: str) -> str:
    value = config.get(key)
    return value if value else default

DEFAULTS = {"linearProject": "QRSPI"}
```

— `scripts/qrspi_config.py:36-42, 33`

```js
  if (typeof env.value !== 'string') return { ok: false, error: `config: envelope value not a string (got ${env.value})` }
```

— `.claude/workflows/qrspi-batch.js:389`

`ciReviseCap` precedent (flat top-level int, default 3, fallback on non-positive/non-integer): config.example.json:5, 33.

**Dependencies:** `qrspi_config.py` ← `parseConfigEnvelope` (JS). `qrspi_critics_config.py` ← `parseCriticsEnvelope` (JS, :403). Both read the same `.qrspi/config.json` (gitignored; only `.qrspi/config.example.json` is committed — there is NO `.qrspi/config.json` in the tree).
**Implicit contracts:** `read_config` NEVER raises (returns `{}`). The single-key reader is string-only; structured/typed config requires a dedicated resolver emitting a typed envelope (the critics-config pattern). New keys SHOULD be documented as `$comment*` blocks in `config.example.json` (the convention there). MEMORY note "Config reader is single-top-level-key only" corroborates this exactly.

---

## Q6: Do the current CLI commands have a shared entry/wrapper point where structured JSON log emission and the `--log-level` / stderr behavior could be installed once rather than per-command?

**Answer:** **No.** There is no shared CLI base/wrapper. Each `scripts/qrspi_*.py` is a fully standalone script with its own `def main()`, its own `argparse.ArgumentParser`, and its own `if __name__ == "__main__": sys.exit(main())` block (e.g. qrspi_persist.py:97-137, qrspi_config.py:59-79, qrspi_ci_revise_bump.py:202-233, qrspi_metrics_append.py:104-153). The only shared module imported across them is `scripts/qrspi_paths.py` (path resolution) — there is no shared CLI/argparse/logging helper.

The closest thing to a uniform convention (not a wrapper, a repeated PATTERN):
- All print ONE JSON envelope to **stdout** via `json.dump(env, sys.stdout, indent=2); print()` and `return 0 if ok else 1`.
- A few scripts use `sys.stderr` ad-hoc (grep: `diagnose.py`, `eval_all.py`, `meta_agent.py`, `qrspi_research_digest.py`, `revise.py`, `run_tests.py`) — but NOT the core `qrspi_*` orchestration scripts, which keep stdout machine-parseable and emit nothing on stderr.
- No script uses Python's `logging` module or a `--log-level` flag (grep for `import logging` / `getLogger` / `--log-level` across `scripts/` returns nothing).

So a `--log-level`/stderr structured-log behavior would have to be installed **per-command** today, OR a new shared module (e.g. `qrspi_obs.py`) created and imported the same way `qrspi_paths` is (`sys.path.insert(0, ENGINE_ROOT); import qrspi_obs`). The import-sibling mechanism exists; the shared CLI scaffold does not.

**Evidence:**

```python
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)
import qrspi_paths  # noqa: E402
```

— `scripts/qrspi_metrics_append.py:52-55` (the ONLY shared-import pattern; repeated verbatim in persist / ci_revise_bump / pr_state etc.)

**Dependencies:** Every script depends on `qrspi_paths` for root resolution; nothing else is shared. The JS orchestrator invokes each via a per-command worker prompt (`engineCmd`/`engineCmdFor`).
**Implicit contracts:** stdout is RESERVED for the single machine-parsed JSON envelope (the worker reads `ok` off stdout — qrspi-batch.js:2153). **Any new human/structured logging MUST go to stderr**, never stdout, or it would corrupt the envelope the orchestrator parses. This is the load-bearing constraint for a `--log-level`/stderr design.

---

## Q7: How is the exponential-backoff retry policy "already defined in the pipeline config" represented and read today, so retry-attempt events can record the same backoff durations rather than recomputing them?

**Answer:** **NOT FOUND — no exponential-backoff retry policy exists anywhere in this codebase.** The premise that one is "already defined in the pipeline config" does not hold against the code.

Search queries attempted (all under REPO_ROOT): `grep -rn "backoff|exponential|sleep|delay|interval|maxRetries|max_retries"` over `scripts/qrspi_*.py` and `.qrspi/config.example.json` → **zero matches**. `grep -rln "backoff|exponential|retry"` over `scripts/`, `.claude/`, `docs/` matches only the literal word "retry" in prose, never a backoff/duration policy.

What DOES exist (and is likely the intended referent, but is NOT a backoff/duration policy):
1. **The CI-revise consecutive-red CAP** — `ciReviseCap` (flat top-level int in `.qrspi/config.json`, default 3; non-positive/non-integer → 3 — config.example.json:5). It is a **count cap**, not a backoff. The `CI-Revise-Attempt: N` head-commit trailer COUNTS consecutive red revises (`qrspi_ci_revise_bump.py` increments it; the gather reads it). Once `N` reaches the cap, the resolver parks the PR (`red → wait`, `ciGaveUp`). There are NO durations — no delay between attempts is computed or stored.
2. **Worker-level "retry once"** — individual worker prompts say "retry once on failure" (e.g. qrspi-batch.js:1398, SKILL.md:63). This is a fixed single retry, no backoff, not configurable.

So a "retry-attempt event" can record the **attempt counter** (`CI-Revise-Attempt: N`, sourced from the head-commit trailer via `qrspi_pr_state.ci_revise_attempt` / `qrspi_ci_revise_bump.parse_ci_revise_attempt`) and the **cap** (`ciReviseCap`), but there are NO backoff durations to mirror — they would have to be invented if the schema requires them.

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

— `scripts/qrspi_ci_revise_bump.py:75-88` (the attempt-counter parse — there is no duration anywhere near it)

config.example.json `$comment_ci`: "'ciReviseCap' (flat top-level key, positive integer, default 3) caps the consecutive autonomous CI-failure revises ... before parking it as 'wait'" — `.qrspi/config.example.json:5`

**Dependencies:** Cap read: `.qrspi/config.json` `ciReviseCap` → resolver. Counter read: head-commit trailer → `qrspi_pr_state.ci_revise_attempt` (gather) → resolver. Counter write: `qrspi_ci_revise_bump.py` (CI path) / `resetCiReviseTrailer` (non-CI path).
**Implicit contracts:** The trailer is the SHARED serialization contract between writer (`qrspi_ci_revise_bump`) and reader (`qrspi_pr_state`): absent ⇒ 0, last-occurrence wins (qrspi_ci_revise_bump.py:61-64). **Inconsistency flagged below** — the question's framing assumes a backoff policy that the code does not implement.

---

## Q8: How is the CI-revise attempt counter (`CI-Revise-Attempt: N` head-commit trailer) currently persisted and reset, and does an event-log emitter need to mirror that state or read it for retry events?

**Answer:** The counter is persisted **only** as a trailer line in the head-commit message of each phase/slice branch (no separate file/DB). It has one canonical regex contract shared by reader and writer: `^CI-Revise-Attempt:\s*(\d+)\s*$` (multiline), last-occurrence wins, absent ⇒ 0.

**Persist (increment) — CI-failure path:** `scripts/qrspi_ci_revise_bump.py` is the SOLE increment authority. `bump_ci_revise_trailer(message)` (pure, unit-tested) strips all existing `CI-Revise-Attempt:` lines and appends exactly one `CI-Revise-Attempt: <prior+1>` (:91-118); `bump_and_publish` checks out the branch, applies a MESSAGE-ONLY amend (`gt modify -m`, the one place a bare `-m` is correct), re-publishes, and VERIFIES exactly one trailer at the new value, failing closed (:150-199). The JS orchestrator drives it via `bumpCiReviseTrailers(t, r, d)` (qrspi-batch.js:2232) — one worker per still-red branch in `r.ciRedBranches`, fired UNCONDITIONALLY after the content worker returns whenever `ciFailing` (so an unfixable red PR still marches to the cap).

**Reset — two resets:**
1. **Read-side reset (gather):** in `qrspi_pr_state.py` the EFFECTIVE `ciReviseAttempt` is forced to `0` whenever `ciState != "red"` (:303-308) — the parsed trailer is only honored when red.
2. **Writer-side reset (non-CI amend):** `resetCiReviseTrailer` (qrspi-batch.js:2180) rewrites the head message to `CI-Revise-Attempt: 0` after any non-CI amend (comment-apply path), idempotent (no-op when absent/already 0).

**Does an emitter need to mirror/read it?** It need only **READ** it — never mirror/own it (the orchestrator already owns the writes; mirroring would risk divergence). For a retry-attempt event, the value is sourced exactly as the resolver sources it: the gather's `ciReviseAttempt` field (effective, red-gated) is already surfaced in the resolve envelope and consumed by `doRevise`. An emitter inside `bumpCiReviseTrailers` could read each worker's returned `{ prior, new }` (`CI_REVISE_BUMP_SCHEMA`, :2204) — the authoritative before/after of each increment, already parsed — without touching the trailer itself.

**Evidence:**

```python
    ci_state = check_rollup_state(node)
    failing = _failing_checks(node) if ci_state == "red" else []
    if ci_state == "red":
        attempt = ci_revise_attempt(_head_commit(node).get("message"))
    else:
        attempt = 0
```

— `scripts/qrspi_pr_state.py:303-308`

```js
    if (!fin || !fin.ok) { ... failures.push({ branch, error }); continue }
    log(`  ${t.id}: CI-Revise-Attempt bumped on ${branch} (${fin.prior ?? '?'} → ${fin.new ?? '?'})`)
    bumped.push({ branch, prior: fin.prior, new: fin.new })
```

— `.claude/workflows/qrspi-batch.js:2248-2255`

**Dependencies:** Writer `qrspi_ci_revise_bump.py` (CI path) + `resetCiReviseTrailer` (non-CI path); reader `qrspi_pr_state.py::ci_revise_attempt` → resolver decision → `r.ciReviseAttempt`/`r.ciRedBranches`. The regex `_CI_REVISE_ATTEMPT_RE` is duplicated VERBATIM in both `qrspi_ci_revise_bump.py:64` and `qrspi_pr_state.py:112` (the shared serialization contract).
**Implicit contracts:** Exactly ONE writer per path (bump on CI, reset on non-CI — qrspi-batch.js:2065-2087); the worker NEVER writes the trailer (RUS-83); the trailer is the only persistence (no sidecar). An emitter must read, not write, to avoid a second authority.

---

## Q9: How is concurrency handled today when multiple ticket agents run in parallel worktrees, and what guarantees the append-only/append-aligned JSONL writes to a single shared `events.jsonl` do not interleave or corrupt records?

**Answer:** Two distinct concurrency facts, and they create a real risk for a SHARED `events.jsonl`:

1. **The qrspi-batch main loop is SEQUENTIAL across tickets.** The per-ticket dispatch loop is a plain `for` loop (qrspi-batch.js:2659), explicitly NOT parallel: "Sequential: tickets share one .git index, so worktree/Graphite ops must not race" (:2655). Within a ticket, the comment-reply / CI-bump loops are ALSO sequential for the same reason (:2119-2120, :2237-2238). So inside a single qrspi-batch invocation, there is effectively ONE writer at a time.
2. **BUT the design explicitly supports multiple CONCURRENT qrspi-batch runs / agents.** Worktrees exist precisely so "multiple agents [can] work on different tickets concurrently" (.claude/CLAUDE.md "Worktrees"). Nothing prevents two `Workflow({name:"qrspi-batch", args:{ticket:...}})` invocations (or `/qrspi-work` sessions) running at once. Today every per-ticket write is ISOLATED to `.worktrees/<id>/.qrspi/<id>/...` (per-ticket ledger — see Q4), so concurrent runs never write the same file. There is **no lock, no flock, no atomic-append guard anywhere** (grep for `flock`/`fcntl`/`lock` in scripts → none).

**The guarantee gap:** A SINGLE shared repo-level `.qrspi/observability/events.jsonl` (Q4's path) would be the FIRST cross-ticket shared write target. The existing `append_line` is a plain `open(path, "a"); fh.write(json.dumps(line) + "\n")` (qrspi_metrics_append.py:88-90) — it relies on per-ticket file isolation, NOT on append atomicity. POSIX guarantees `O_APPEND` writes under `PIPE_BUF` (4096 bytes) are atomic, but a JSONL event line could exceed that, and the helper does not open with explicit `O_APPEND` / `os.write` semantics — it uses buffered Python `open(..., "a")`. So **nothing in the codebase today guarantees non-interleaving for a shared file**; the current safety comes entirely from per-ticket path isolation, which the proposed shared path would break.

**Evidence:**

```js
// Sequential: tickets share one .git index, so worktree/Graphite ops must not race.
const results = []
...
for (let i = 0; i < tickets.length; i++) {
```

— `.claude/workflows/qrspi-batch.js:2655-2659`

```python
    with open(path, "a") as fh:
        fh.write(json.dumps(ledger_line) + "\n")
```

— `scripts/qrspi_metrics_append.py:89-90` (plain buffered append; no lock, relies on per-ticket isolation)

**Dependencies:** Worktree provisioning: `scripts/qrspi_provision.py` (re-provisioned per worker, qrspi-batch.js:118). Root resolution always yields the MAIN checkout (`qrspi_paths`), so a repo-level shared file WOULD be a single physical target across worktrees.
**Implicit contracts:** Per-ticket isolation is the de-facto concurrency model — there is no inter-process lock. A shared `events.jsonl` must introduce its own atomicity guarantee (single-line-per-write with `O_APPEND`+`os.write` under PIPE_BUF, or an OS file lock), because the codebase provides none. **Inconsistency flagged below.**

---

## Q10: What happens to the event log writer when a phase worker crashes mid-write or the process is killed, and is there an existing pattern for crash-safe file appends elsewhere in the codebase?

**Answer:**
**Today, on crash:** there is NO event log writer, so nothing. For the existing analogous writers the failure model is:
- `runPhase` uses **staging + atomic move** (`qrspi_persist.py`): the artifact is fully written to `/tmp/phase-stage/<id>/<name>.md` first, then `shutil.move`d to the canonical dest (qrspi_persist.py:84-85). A crash before the move leaves NO partial canonical file; the persist gate (`p.ok`) catches a missing/empty artifact and `runPhase` returns `false` (:1369-1373). This is crash-safe BY CONSTRUCTION for whole-file artifacts (the move is the commit point).
- `qrspi_metrics_append.py` appends with plain buffered `open(..., "a")` + verify-non-empty (:88-99). A crash mid-write could leave a truncated final line; there is no fsync, no temp-then-rename, no atomic append. The verify only checks the file is non-empty, NOT that the last line is valid JSON. Best-effort: a metrics-append failure is logged, never silently dropped, but a torn last line would survive.
- The per-ticket `try/catch` (qrspi-batch.js:2667-2724) catches a thrown/killed worker at the JS level and records `action: 'errored'`, but it cannot un-write a partial disk write a python subprocess already made.

**Existing crash-safe pattern:** The **staging-then-move** pattern (`qrspi_persist.py`, the "Fix A" the whole harness is built around) is the codebase's crash-safe idiom — but it is for **whole-file replace**, not append. There is NO crash-safe APPEND pattern (no temp-line + rename, no fsync, no atomic O_APPEND under PIPE_BUF) anywhere. JSONL recovery is implicitly "a reader skips/tolerates a malformed trailing line," but no reader-side tolerance is implemented either (the metrics ledger is only ever appended, never re-read by the harness except by the summary tool, which is out of the batch path).

**Evidence:**

```python
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(src, dest)
    try:
        out = os.path.getsize(dest)
    except OSError:
        return 0, "destination not written: %s" % dest
```

— `scripts/qrspi_persist.py:84-89` (staging+move = the crash-safe whole-file commit point)

```python
    with open(path, "a") as fh:
        fh.write(json.dumps(ledger_line) + "\n")
    try:
        size = os.path.getsize(path)
    ...
    if size == 0:
        return 0, 0, "ledger is empty after append: %s" % path
```

— `scripts/qrspi_metrics_append.py:88-96` (append: verify-non-empty only; NO torn-line / fsync protection)

**Dependencies:** `runPhase` ← `qrspi_persist.py` (move-based, crash-safe). Metrics ← `qrspi_metrics_append.py` (append, NOT crash-safe against a torn final line).
**Implicit contracts:** Whole-file artifacts get atomic-move crash-safety; append targets get only non-empty verification. An event writer choosing append must add its own torn-line tolerance (write a single line per call; line-buffered or `os.write` of one assembled bytes blob) since the codebase offers no append crash-safety precedent. JSONL's natural recovery (drop the final partial line) is the conventional mitigation but is NOT implemented here today.

---

## Q11: How does log rotation interact with in-flight writers — what determines which file is "current" when a rotation triggers at the configured size, and how is a partially-written final record at rotation boundary handled?

**Answer:** **NOT FOUND — no log rotation exists in the codebase.** Search queries (under REPO_ROOT): `grep -rn "rotat|rotation"` over `scripts/`, `.claude/`, `.qrspi/config.example.json` → zero matches; `grep "RotatingFileHandler|logging.handlers"` → none; no `.jsonl` writer truncates, renames-on-size, or checks a size threshold (`qrspi_metrics_append.py` appends unboundedly with no size check — :88-99). There is no "current file" pointer, no `events.1.jsonl`/`events.2.jsonl` scheme, no max-size config key anywhere.

Consequently there is no existing mechanism that determines "which file is current" or that handles a partial record at a rotation boundary — both would be entirely NEW. The closest adjacent facts that constrain a future design:
- The only size-related config precedent is `ciReviseCap` (a COUNT cap, not a byte size — config.example.json:5); there is no byte-size config anywhere.
- The append helper (`append_line`) is the only writer of a `.jsonl`; it does not consult any rotation policy.

So a rotation design would be greenfield: it must define the current-file selection, the rotate-on-size trigger, and the partial-final-record handling from scratch. Given Q9/Q10, the partial-record-at-boundary case has no existing guard to build on.

**Evidence:**

```python
def append_line(path, ledger_line):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(ledger_line) + "\n")
    ...
```

— `scripts/qrspi_metrics_append.py:82-90` (the only `.jsonl` writer — appends unboundedly, no size check, no rotation)

`grep -rn "rotat|rotation|RotatingFileHandler"` over the repo → no results.

**Dependencies:** None exist. A rotation writer would depend on the same `qrspi_paths` root resolution and would have to introduce its own size-config reader (per Q5, a structured `observability` block via a dedicated resolver, since `qrspi_config.py` is string-single-key only).
**Implicit contracts:** None established. Any rotation must define, from scratch: current-file naming, size trigger evaluation timing (per-write vs periodic), and boundary handling — none of which has a codebase precedent to mirror.

---

## Q12: What is the existing unit-test convention (`scripts/*_test.py`, stdlib-only, run via `scripts/run_tests.py`), and how do current tests exercise file-writing scripts like `qrspi_persist.py` without polluting the real `.qrspi/` tree?

**Answer:** Convention is precise and uniform:
- Each script has a `scripts/<name>_test.py` sibling, **stdlib-only** (`unittest`, no pytest/third-party — confirmed by `tests.yml`: "no dependency-install step"). Each is a standalone `python3 scripts/<name>_test.py` exiting 0/non-zero.
- `scripts/run_tests.py` is the aggregating runner: discovers every `scripts/*_test.py`, runs each as its OWN subprocess, prints PASS/FAIL per file, exits non-zero if any fail (run_tests.py:1-18, `DEFAULT_TIMEOUT = 180`). Filter by substring (`python3 scripts/run_tests.py persist`), `--list` to enumerate. This is the CI gate (`.github/workflows/tests.yml` `python` job).
- Tests import the module directly after `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` (qrspi_config_test.py:14-16) and exercise the **pure helpers** (the modules are deliberately split into pure functions + a thin I/O `main`).

**Avoiding `.qrspi/` pollution:** The dominant idiom is `tempfile.TemporaryDirectory()` as a synthetic repo root, with the pure path helpers (`staging_path`, `dest_path`, `ledger_path`) fed that temp root so NO write ever touches the real tree:
- `qrspi_persist_test.py` stages into `<tmp>/stage/...` and persists into `<tmp>/.worktrees/...`, asserting bytes/move/empty-rejection entirely under the `TemporaryDirectory` (`setUp`/`tearDown` at :49-54, `_stage` at :56-61).
- It also proves the host-root divergence with a SYNTHETIC `host_root = "/synthetic/host-checkout"` passed to the PURE `dest_path` (no real FS touch — :33-45).
- `qrspi_config_test.py` writes config into a temp `<tmp>/.qrspi/config.json` and asserts `read_config` never touches the real repo (:46-60, docstring "Never touches the real repo config").

So the convention for a file-writing script is: split a PURE path/format helper from the I/O `main`, unit-test the pure helper against `tempfile` roots, and (for the subprocess/`gt`/`gh` mechanics) leave them to manual e2e (e.g. `qrspi_ci_revise_bump.py` marks its subprocess section "not unit-tested; manual e2e" — :134).

**Evidence:**

```python
class PersistTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
    def tearDown(self):
        self.tmp.cleanup()
    def _stage(self, ticket, artifact, content):
        src = qp.staging_path(os.path.join(self.root, "stage"), ticket, artifact)
        os.makedirs(os.path.dirname(src), exist_ok=True)
        ...
```

— `scripts/qrspi_persist_test.py:48-61`

**Dependencies:** `run_tests.py` (runner/CI gate) ← every `*_test.py`. Tests ← the pure helpers of their target module. No test depends on network/`gh`/`gt`.
**Implicit contracts:** (1) stdlib-only — adding a third-party import would break the no-install CI job; (2) pure-helper/IO-main split is REQUIRED for testability (the I/O main and subprocess mechanics are NOT unit-tested); (3) tests must use `tempfile` and never write the real `.qrspi/` tree; (4) a new file-writing script MUST ship a `_test.py` sibling exercising its pure path/format/rotation helpers against temp roots, or `run_tests.py`/CI gives it zero coverage.

---

## Q13: Does the codebase already emit any logs, traces, or structured output today (and to where), so the new structured logging does not duplicate or conflict with existing output that interactive users or CI rely on?

**Answer:** Yes, several distinct output channels already exist; a new structured log must not collide with any:

1. **Orchestrator human log (stdout, runner-injected `log()`):** qrspi-batch.js calls `log(...)` extensively (e.g. :2635 "Found N ticket(s)", :2691 "decision=...", :2719 the per-ticket result line). These are human-readable progress lines surfaced to whoever runs the batch. They are NOT structured/JSON.

2. **Per-command JSON envelopes (stdout, machine-parsed):** every `scripts/qrspi_*.py` prints exactly one JSON envelope to stdout, which the orchestrator parses with the `parse*Envelope` validators (Q2). **stdout is reserved and load-bearing** — extra stdout noise breaks parsing (the workers are told "Output that JSON ... NO surrounding prose, NO code fences").

3. **The critic-metrics ledger (`.qrspi/<id>/critic-metrics.jsonl`):** the ONLY existing structured/append-only data sink (`qrspi_metrics_append.py`, RUS-77/78), one JSON line per terminated critic step, stamped with `runId`. A new `events.jsonl` would be a SECOND structured sink — it should complement, not duplicate, this (the metrics ledger is critic-step-scoped; events would be phase-transition-scoped).

4. **CI output (`.github/workflows/tests.yml`):** two jobs — `python` runs `python3 scripts/run_tests.py` (relies on its PASS/FAIL stdout + exit code), `workflow-syntax` runs `node scripts/check_workflows.js`. CI depends on exit codes and test runner stdout; new logging on stderr won't conflict, new stdout noise from a test could.

5. **Ad-hoc stderr in non-core scripts:** `diagnose.py`, `eval_all.py`, `meta_agent.py`, `qrspi_research_digest.py`, `revise.py`, `run_tests.py` write to `sys.stderr` — but the CORE qrspi orchestration scripts (`qrspi_persist`/`qrspi_resolve`/`qrspi_config`/`qrspi_ci_revise_bump`/`qrspi_metrics_append`) emit NOTHING on stderr, keeping stderr free.

**Conflict-avoidance conclusion:** stderr is the safe channel for new human/structured log lines in the core scripts (it is currently empty for them and unused by CI parsing). stdout is OFF-LIMITS for anything but the existing single JSON envelope. A new `events.jsonl` file sink does not collide with any existing FILE (the only other structured file is the per-ticket `critic-metrics.jsonl`).

**Evidence:**

```js
log(`Found ${tickets.length} ticket(s): ${tickets.map(t => `${t.id} (${t.status})`).join(', ') || '(none)'}`)
```

— `.claude/workflows/qrspi-batch.js:2635` (human stdout log via injected `log`)

```
      - name: Run Python test suite
        run: python3 scripts/run_tests.py
```

— `.github/workflows/tests.yml` `python` job (CI depends on this exit code + stdout)

**Dependencies:** stdout ← parsed by `parse*Envelope` (JS) and by CI. The metrics ledger ← `qrspi_critic_summary.py`. No tracing/OTel libs are imported anywhere.
**Implicit contracts:** stdout of any `qrspi_*.py` invoked by the orchestrator MUST be exactly one JSON envelope (no log lines). stderr is free in the core scripts and is the correct channel for `--log-level` human/structured output. The existing `critic-metrics.jsonl` establishes the JSONL-event-sink precedent a new `events.jsonl` should follow (same dir convention, same `runId` stamping).

---

## Discovered Patterns

- **Self-locating script idiom (universal):** every `scripts/qrspi_*.py` resolves its host root via `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` (git-common-dir → MAIN checkout, never a worktree) after `sys.path.insert(0, ENGINE_ROOT)`. The qrspi-laden path is ALWAYS computed by the script, never typed by a model (the "Fix A" / path-mangling-defense that the whole harness is built on — see qrspi_persist.py:1-29).
- **stdout = one JSON envelope, exit code mirrors `ok`:** the universal CLI contract. Workers read `ok` off stdout, not the exit code alone.
- **Pure-helper / thin-IO-main split:** every script isolates pure functions (path builders, parsers, reducers) from the subprocess/IO `main`, so the pure parts are stdlib-unit-tested against `tempfile` roots and the `gt`/`gh` mechanics are left to manual e2e.
- **JS delegates ALL disk/subprocess work to single-command workers:** the sandbox cannot run python/shell; each side effect is one `agent()` worker running ONE verbatim `engineCmd`/`engineCmdFor` command and returning JSON, re-validated by a `parse*Envelope` function. A `null`/garbled worker result degrades to a clean `{ok:false}`, never a throw.
- **Resume-safety:** workflow scripts forbid `Date.now()`/`Math.random()`; ids use `crypto.randomUUID`/`getRandomValues` or injected env (`runId`, qrspi-batch.js:130-141).
- **`runId` is the existing correlation key:** computed once per invocation, already stamped on every metrics ledger line — the natural anchor for a trace/event correlation id.
- **Per-ticket file isolation is the de-facto concurrency model:** all `.qrspi/` writes live under `.worktrees/<id>/.qrspi/<id>/`, so concurrent worktrees never share a write target — there are no file locks anywhere.
- **Config is read flat-single-key (`qrspi_config.py`) OR via a dedicated typed resolver (`qrspi_critics_config.py`):** structured multi-value config uses the resolver pattern; the single-key reader is string-only and rejects nested/non-string values.
- **Append-only JSONL ledger precedent already exists** (`qrspi_metrics_append.py`) — the closest template for an events writer, though per-ticket-scoped and without rotation/lock/torn-line guards.

## Inconsistencies

- **Q7 premise vs reality — no exponential-backoff retry policy exists.** The question assumes "an exponential-backoff retry policy already defined in the pipeline config." Grep across the entire repo finds NO backoff/delay/sleep/interval/exponential logic and no duration config. The only retry-with-bound is `ciReviseCap` — a consecutive-red COUNT cap, not a backoff/duration policy — plus fixed "retry once" prose in worker prompts. An event schema requiring backoff durations would have to invent them.
- **Q11 premise vs reality — no log rotation exists.** No rotation, size-threshold, current-file selection, or RotatingFileHandler anywhere; the sole `.jsonl` writer appends unboundedly. Rotation + partial-record-at-boundary handling are entirely greenfield.
- **Q9 shared-file concurrency gap.** The proposed single `.qrspi/observability/events.jsonl` (no `<id>` segment) breaks the per-ticket file-isolation model that is currently the ONLY concurrency guarantee. The existing `append_line` uses plain buffered `open(..., "a")` with no `O_APPEND`/lock/fsync — it is interleave-safe today only because no file is shared across tickets. A shared event log needs a NEW atomicity guarantee the codebase does not provide.
- **Crash-safety asymmetry (Q10).** Whole-file artifacts get atomic-move crash-safety (`qrspi_persist.py` staging+`shutil.move`), but the append path (`qrspi_metrics_append.py`) only verifies non-empty — a torn final line at a crash boundary would survive, and no reader tolerates it. Append crash-safety has no precedent to copy.
- **stdout dual-use tension (Q6/Q13).** The orchestrator's human `log()` lines AND every python script's machine-parsed JSON envelope both target stdout in different contexts; the invariant that holds them apart is "a `qrspi_*.py` invoked by the orchestrator prints ONLY its JSON envelope on stdout." New structured logging must go to stderr to preserve this — but several non-core scripts already use stderr ad-hoc, so there is no single owned stderr-logging convention either.
- **`ciReviseCap` config-read mechanism is unstated.** It is a flat top-level INT in `.qrspi/config.json`, but `qrspi_config.py` + `parseConfigEnvelope` are string-single-key only (they would REJECT a non-string value). The example file documents `ciReviseCap` but the code path that actually reads it as an int is not the `qrspi_config.py` path — a new int/structured `observability` config must NOT assume the `qrspi_config.py` reader can return it.
