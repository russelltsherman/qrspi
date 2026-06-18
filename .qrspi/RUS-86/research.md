# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Q1: Where in the pipeline are phase transitions (start, end, success, failure, retry) currently triggered, such that a structured JSONL event could be emitted at each one?

**Answer:** Phase transitions are driven entirely from the JS orchestrator `.claude/workflows/qrspi-batch.js`. The decision (`run_design | advance | submit | reset | revise | land | wait | entry_blocked`) is computed by the tested Python resolver and dispatched by a `switch` in the main per-ticket loop. Each branch calls a `do*` handler (`doDesign`, `doPlan`, `doImplementation`, `doSubmit`, `doReset`, `doRevise`, `doLand`). Within a phase, the real per-phase success/failure gate is `runPhase()` — it spawns the typed agent, runs optional critic/node-check stages, then persists the artifact (persist is "the real success gate"). There is **no event emission today**; the only durable per-step record is the critic-metrics ledger (see Q14). Transition points where a JSONL event could attach: the dispatch `switch` (start), each `do*` handler's return (success/skip), `runPhase` success/failure returns, and `doRevise`'s CI-revise counter bump (retry).

**Evidence:**

```
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
      case 'reset': res = await doReset(t, r); break
      case 'revise': res = await doRevise(t, r); break
      case 'land': res = await doLand(t, r); break
```

— `.claude/workflows/qrspi-batch.js:2675-2688`

```
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

— `.claude/workflows/qrspi-batch.js:1290-1299`

**Dependencies:** `qrspi-batch.js` is the upstream driver; it calls the Python decision authority `scripts/qrspi_resolve.py` (which folds in `qrspi_pr_state.py` + `qrspi_resolve_state.py`). The `do*` handlers spawn typed agents in `.claude/agents/`. Direction: JS orchestrator → Python resolver → typed agents.
**Implicit contracts:** Each ticket advances **at most ONE autonomous step per run** (`.claude/workflows/qrspi-batch.js:36-37`). `runPhase` is fail-closed: a missing staged artifact stops the ticket. `log()` and `phase()` are harness-provided globals (not defined in the file); any event emitter must either piggyback on these or shell out to a Python helper (the JS sandbox cannot run Python directly — it delegates to worker agents / `agent()` shell-outs).

## Q2: How are `trace_id`, `span_id`, and `parent_span_id` values currently generated or propagated, if at all, across a ticket lifetime and its child operations (phases, commands, critic runs)?

**Answer:** There is **no trace/span model today**. The closest existing concept is `runId` — a single per-invocation id computed once at the top of `qrspi-batch.js` and stamped onto every appended critic-metrics ledger line. It is `QRSPI_RUN_ID` env var when set, else `crypto.randomUUID()`, else a `crypto.getRandomValues`-derived `run-<hex>`, else the constant `'run-fallback'`. **`Date.now()` / `Math.random()` are explicitly forbidden** (they break workflow resume). There is no per-phase or per-child-operation id, no parent/child linkage — `runId` is run-scoped, not ticket-scoped or span-scoped. The only ticket-scoped id is the Linear `ticket.id` (e.g. `RUS-86`) carried through as `t.id`/`id`. `agent()` calls carry a human-readable `label` (e.g. `critic:${id}:${name}:${lens}#${round+1}`) and a `phase` tag, but these are display labels, not propagated correlation ids.

**Evidence:**

```
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

— `.claude/workflows/qrspi-batch.js:118-126`

**Dependencies:** `runId` is consumed only by the critic-metrics append shell-out (`scripts/qrspi_metrics_append.py --run-id '${runId}'`, `.claude/workflows/qrspi-batch.js:980`). `qrspi_metrics_append.py:wrap_envelope()` stamps it as the `runId` field on each ledger line.
**Implicit contracts:** "runId always present, always a string" (`.claude/workflows/qrspi-batch.js:113`). `qrspi_metrics_append.py` **requires** `--run-id` (`required=True`, `scripts/qrspi_metrics_append.py:111-113`). Forbidden APIs for id generation: `Date.now()`, `Math.random()` (workflow-resume safety — `.claude/workflows/qrspi-batch.js:115-117`, and project memory "qrspi-batch runId Date.now bug"). Any new trace/span scheme must follow the same crypto-guarded, no-timestamp pattern to remain resume-safe.

## Q3: What identifiers for `ticket_id`, `phase`, and `actor` are already available at each phase-transition point that the event schema requires?

**Answer:** At each transition point: **`ticket_id`** is available as `t.id` / `id` (Linear identifier, e.g. `RUS-86`), validated by `TICKETS_SCHEMA` (`id` required string). **`phase`** is available in two forms — the decision's `decision.phase` / `decision.nextPhase` (machine values `design | plan | implementation`), and the orchestrator's display `phaseLabel` passed to `runPhase` / `agent({ phase })` (`Design | Plan | Implementation | Critic | Resolve | Restack | Finalize`). **`actor`** is **not modeled as a field**; the nearest proxy is the `agent()` `label` (e.g. `design:RUS-86`, `critic:RUS-86:design:simplicity#1`) and `agentType` (the registered `.claude/agents/qrspi-*` type). The run is also identified by `runId` (Q2). There is no explicit human-vs-bot actor field anywhere.

**Evidence:**

```
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
```

— `.claude/workflows/qrspi-batch.js:1295`

```
        required: ['id', 'title', 'status', 'createdAt'],
        properties: {
          id: { type: 'string' },
```

— `.claude/workflows/qrspi-batch.js:191-193`

**Dependencies:** `decision.{action,phase,nextPhase,...}` originates in `scripts/qrspi_resolve_state.py` and is surfaced through `qrspi_resolve.py`'s envelope (documented at `.claude/workflows/qrspi-batch.js:208-215`). `phaseLabel` is a literal passed by each `do*` handler.
**Implicit contracts:** The phase vocabulary is split: machine phase names are lowercase (`design`/`plan`/`implementation`) in the resolver envelope; orchestrator display phases are Titlecase (`Design`/`Plan`/...). The `phase()` harness call uses the Titlecase form (e.g. `phase('Resolve')`, `.claude/workflows/qrspi-batch.js:1367`). An event schema needs to pick one and map; the resolver's lowercase machine phase is the more stable contract (it is unit-tested).

## Q4: What configuration-reading mechanism exists today for nested keys like `observability.eventLog`, given that the config reader handles only single top-level keys?

**Answer:** **NOT FOUND as a nested reader — confirmed single-top-level-key only.** `scripts/qrspi_config.py` reads exactly ONE flat top-level key via `--key`, with a per-key default table; `select_value()` does `config.get(key)` with no dot-path support. The JS side shells out `python3 scripts/qrspi_config.py --key linearProject` and parses one JSON line. The other config consumer, `qrspi_resolve.py:load_ci_revise_cap()`, also reads a SINGLE flat key (`config.get("ciReviseCap")`). There is a richer **nested** reader for ONE specific block — `scripts/qrspi_critics_config.py` — which parses the nested `critics.design.{...}` / `critics.implementation.coherence.{...}` structure, but it is purpose-built for the critics block, not a general nested-key utility. A new `observability.eventLog.*` block would need either a new purpose-built resolver (mirroring `qrspi_critics_config.py`) or an extension to `qrspi_config.py`; reading it via the existing single-key `qrspi_config.py` is impossible without code change.

**Evidence:**

```
def select_value(config: dict, key: str, default: str) -> str:
    """Pure selector: return config[key] when present and truthy, else default.
    ..."""
    value = config.get(key)
    return value if value else default
```

— `scripts/qrspi_config.py:36-42`

```
def load_ci_revise_cap(repo_root=REPO_ROOT):
    """Resolve the `ciReviseCap` from <repo>/.qrspi/config.json (a SINGLE flat
    top-level key — the reader handles no dot-path; ref: project memory) ..."""
    config = qrspi_config.read_config(repo_root)
    return coerce_cap(config.get("ciReviseCap"))
```

— `scripts/qrspi_resolve.py:405-411`

**Dependencies:** `qrspi_config.read_config()` is the shared best-effort JSON loader reused by `qrspi_resolve.py` and `qrspi_critics_config.py`. It returns `{}` on any error (never raises).
**Implicit contracts:** Config file is `<repo_root>/.qrspi/config.json`, gitignored (per `.gitignore`), with `config.example.json` as the committed reference. A non-dict top-level JSON falls back to `{}` (`scripts/qrspi_config.py:54`). The JS `parseConfigEnvelope` path rejects non-string values (project memory "Config reader is single-top-level-key only"). The precedent for a nested block is `qrspi_critics_config.py`, which does its OWN nested parse + type-guards + default-fallbacks rather than asking `qrspi_config.py` for a dot-path.

## Q5: How are environment variables such as `QRSPI_LOG_LEVEL` currently read and defaulted elsewhere in the pipeline, and where would CLI log-level resolution hook in?

**Answer:** Env-var reads are rare and follow two distinct patterns. In **JS** (`qrspi-batch.js`), env vars are read defensively via `typeof process !== 'undefined' && process.env && process.env.X`, OR-chained with fallbacks — used for `CLAUDE_PLUGIN_ROOT` (engine root) and `QRSPI_RUN_ID` (run id). In **Python**, the only env read is `scripts/grade.py:load_api_key()` using `os.environ.get(ANTHROPIC_API_KEY_ENV)` with a `.env`-file fallback. There is **no existing `QRSPI_LOG_LEVEL`** or any log-level concept anywhere. A CLI log-level would most naturally hook in (a) in JS at the top of `qrspi-batch.js` next to the `runId` definition using the same defensive `process.env` OR-chain, and (b) in Python via a small shared helper mirroring the `os.environ.get(...)` + default pattern, since each script self-locates and there is no shared CLI entry point (see Q6).

**Evidence:**

```
const runId =
  (typeof process !== 'undefined' && process.env && process.env.QRSPI_RUN_ID) ||
  (typeof crypto !== 'undefined' && crypto.randomUUID && crypto.randomUUID()) ||
```

— `.claude/workflows/qrspi-batch.js:118-120`

```
    env_value = os.environ.get(ANTHROPIC_API_KEY_ENV)
```

— `scripts/grade.py:825`

**Dependencies:** No central env-config module exists; reads are inline at point of use.
**Implicit contracts:** JS env reads MUST be `typeof`-guarded (the sandbox may not expose `process`). Python env reads default-and-fall-back rather than raising. There is no precedent for a numeric/ordinal log level — the codebase has no logging-level vocabulary to reuse, so any `QRSPI_LOG_LEVEL` semantics are greenfield.

## Q6: What is the existing surface for the "qrspi CLI commands" — is there a single CLI entry point the new logger would attach to, or are commands dispatched per skill/script?

**Answer:** There is **no single CLI entry point**. "qrspi" is dispatched two ways, neither a unified CLI: (1) **Slash-command skills** under `.claude/skills/` (e.g. `qrspi-design`, `qrspi-research`, `review`, `review-design`) — markdown SKILL.md files invoked by Claude Code; (2) **Standalone Python scripts** under `scripts/` (~40 `qrspi_*.py` files), each with its own `argparse` `main()` and `if __name__ == "__main__"` guard, invoked individually (e.g. `python3 scripts/qrspi_persist.py --ticket ... --artifact ...`). The JS workflows (`qrspi-batch.js`, `qrspi-teeth-eval.js`) are a third dispatch surface, run via the Workflow tool. Each Python script self-locates the repo root from `__file__`. The aggregating `scripts/run_tests.py` is the only "runs many scripts" utility, but it runs *tests*, not a command dispatcher. A logger that must attach to "every qrspi command" has no single chokepoint today — it would need to be a shared importable helper that each script/handler calls, not a wrapper around one CLI.

**Evidence:**

```
$ ls .claude/skills/
qrspi-design  qrspi-feature  qrspi-implement  qrspi-plan  qrspi-pr
qrspi-questions  qrspi-research  qrspi-structure  qrspi-ticket  qrspi-work
qrspi-worktree  review  review-design  review-implementation  review-plan
```

— directory listing, `.claude/skills/`

```
if __name__ == "__main__":
    sys.exit(main())
```

— `scripts/qrspi_persist.py:136-137` (the per-script entrypoint pattern, repeated across all `scripts/qrspi_*.py`)

**Dependencies:** Skills (`.claude/skills/*/SKILL.md`) wrap agents (`.claude/agents/qrspi-*.md`); the batch workflow spawns agents and shells out to the Python scripts. Direction: skill/workflow → agent → Python script.
**Implicit contracts:** Every Python tool is stdlib-only, self-locating, prints a single JSON envelope to stdout, exits 0/non-0, and has a `_test.py` sibling. A new logger attaching at the Python layer should be importable (a `qrspi_*` module with pure helpers + a thin CLI) to fit this convention; attaching at the JS layer means a shell-out from the orchestrator (the JS sandbox cannot do file I/O directly — it delegates).

## Q7: How is the exponential-backoff retry policy "already defined in the pipeline config" currently represented and consumed, so retry events can capture `retry_attempt` and `backoff_seconds`?

**Answer:** **NOT FOUND — there is no exponential-backoff retry policy in the pipeline config.** Searches for `backoff`, `exponential`, `retry_attempt`, `retry`, `ciReviseCap` returned two unrelated mechanisms: (1) The **CI-revise CAP** — a *counter*, not a backoff. A `CI-Revise-Attempt: N` head-commit git trailer counts consecutive red-CI revises; `ciReviseCap` (flat top-level config key, default 3) bounds them; once reached, the resolver parks the PR as `wait` (no delay, no backoff seconds — it just stops). Managed by `scripts/qrspi_ci_revise_bump.py`, `qrspi_resolve_state.py:ci_revise_attempt_of()`, and `qrspi_resolve.py:coerce_cap()/load_ci_revise_cap()`. (2) The **LLM-judge backoff** in `scripts/grade.py:call_with_retry()` — a real `time.sleep(JUDGE_BACKOFF_BASE * (2 ** attempt))` exponential backoff, but it is internal to the *eval/grading* harness (not the phase pipeline) and its constants are module-level, **not config-driven**. So there is no config-defined backoff for phase transitions to read `backoff_seconds` from; only the CI-revise attempt counter could supply a `retry_attempt`-like value.

**Evidence:**

```
def coerce_cap(value):
    """Coerce a config `ciReviseCap` value into a positive int, falling back to the
    documented default (3)..."""
    if isinstance(value, bool) or not isinstance(value, int):
        return CI_REVISE_CAP_DEFAULT
    return value if value > 0 else CI_REVISE_CAP_DEFAULT
```

— `scripts/qrspi_resolve.py:393-402`

```
            if attempt < JUDGE_MAX_ATTEMPTS - 1:
                time.sleep(JUDGE_BACKOFF_BASE * (2 ** attempt))
    raise last_exc
```

— `scripts/grade.py:880-882`

**Dependencies:** The cap counter flows: gather (`qrspi_pr_state.py`, reads the trailer, zeroes when not-red) → `qrspi_resolve_state.py:ci_revise_attempt_of()` (aggregates per-slice via `max`) → resolver decision (`revise` vs `wait`). The bump writer is `qrspi_ci_revise_bump.py`. `grade.py`'s backoff is isolated to the judge client.
**Implicit contracts:** The cap counter has two resets (read-side in the gather when rollup ≠ red; writer-side in `doRevise` on any non-CI amend). The trailer is written by a separate message-only `gt modify -m` after the content amend (CLAUDE.md). Any "retry_attempt" event field would map to `CI-Revise-Attempt`; "backoff_seconds" has **no source** in the phase pipeline (would be a fabricated/zero field). The ticket's premise that backoff is "already defined in the pipeline config" appears inaccurate — flag for design.

## Q8: What directories under `.qrspi/` exist or are created at runtime today, and how is `.qrspi/observability/` (plus the `archive/` subdirectory) expected to be created and gitignored?

**Answer:** Committed `.qrspi/` contents: `templates/` (artifact templates), `config.example.json`, and per-ticket `RUS-*/` artifact dirs. Runtime-created dirs: per-ticket artifact dirs are created **inside worktrees** at `<root>/.worktrees/<id>/.qrspi/<id>/` by `qrspi_persist.py:persist()` via `os.makedirs(os.path.dirname(dest), exist_ok=True)`, and the critic-metrics ledger dir likewise by `qrspi_metrics_append.py:append_line()`. The gitignore does **not** ignore `.qrspi/` broadly — it ignores only `.qrspi/config.json` and `.qrspi/features/` (and the whole `.worktrees/` tree). So a NEW `.qrspi/observability/` (and `archive/`) created at the **repo/worktree root** would be **git-tracked unless explicitly added to `.gitignore`**. There is **no existing `.qrspi/observability/` directory and no code that creates one** — it is greenfield. The established creation idiom is `os.makedirs(..., exist_ok=True)` at write time (lazy, fail-closed verify after).

**Evidence:**

```
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(src, dest)
```

— `scripts/qrspi_persist.py:84-85`

```
.worktrees/
.claude/scheduled_tasks.lock
# Local config override (per-user); see .qrspi/config.example.json
.qrspi/config.json
# Local /qrspi-feature elicitation scratch (per-user, pre-ticket)
.qrspi/features/
```

— `.gitignore` (the full set of `.qrspi/`-related ignores)

**Dependencies:** Persist/append both resolve the host root via `qrspi_paths.resolve_repo_root()` (git-common-dir first) so paths land in the MAIN checkout, not a double-nested worktree path (`scripts/qrspi_metrics_append.py:18-28`).
**Implicit contracts:** Directories are created lazily at first write (`exist_ok=True`), never provisioned up front. Anything written under a worktree's `.qrspi/<id>/` is inside the gitignored `.worktrees/` tree (so not tracked); anything written at the repo-root `.qrspi/observability/` would be tracked unless a new `.gitignore` entry is added. The codebase convention is to add a commented `.gitignore` line per per-user/runtime path (see the existing `config.json`/`features/` entries).

## Q9: How does the codebase currently guarantee single-line, flushed-before-continue writes, and what happens to a partially written JSONL line if the process crashes mid-write?

**Answer:** The only JSONL writer today is `qrspi_metrics_append.py:append_line()`. It guarantees **single-line** by writing `json.dumps(ledger_line) + "\n"` (one `json.dumps`, no embedded newlines since the dict is flat). It does **NOT** explicitly flush or `fsync` — it relies on the `with open(path, "a") as fh:` context manager's close to flush to the OS buffer. There is **NO `os.fsync` anywhere in the repo** (grep for `fsync`/`flush` found none in scripts). After writing, it re-opens and counts lines as a non-empty verify (fail-closed), but that verifies *append succeeded*, not durability. **On a mid-write crash:** `"a"` (append) mode means the OS-level write of one `write()` call for a short line is typically atomic at the page level, but Python/stdlib gives NO formal guarantee — a crash between `write()` and `close()`/flush could leave a truncated/partial last line, which a downstream `json.loads` per line would reject. There is no crash-recovery or partial-line repair logic. The general non-JSONL pattern for atomic file replacement exists once: `qrspi_clear_stale_pr.py` writes to a temp file then renames (`open(tmp,"w")` at line 118), but that is whole-file, not append.

**Evidence:**

```
def append_line(path, ledger_line):
    """Append ``ledger_line`` (a dict) as one JSON line to ``path``, creating the
    parent dir, then verify the file is non-empty. ... Fail-closed: a write that
    leaves the ledger empty returns an error."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(ledger_line) + "\n")
    try:
        size = os.path.getsize(path)
    except OSError:
        return 0, 0, "ledger not written: %s" % path
```

— `scripts/qrspi_metrics_append.py:82-94`

**Dependencies:** `append_line` is pure-filesystem (no network/subprocess), unit-tested against temp dirs.
**Implicit contracts:** "one JSON line per record"; lines are independently parseable (`json.loads(lines[i])`, per `qrspi_metrics_append_test.py:102`). Fail-closed = a write leaving the file empty returns an error. **Gap to flag for design:** no flush/fsync, no atomic-append guarantee, no partial-line handling — the ticket's "flushed-before-continue" and crash-safety requirements are NOT met by the current precedent and would be new behavior.

## Q10: What handles concurrent writers to the same path today, given that multiple ticket worktrees run agents concurrently — could two processes append to the same `events.jsonl` or trigger rotation simultaneously?

**Answer:** **Nothing handles concurrent writers — there is NO locking anywhere** (grep for `flock`/`fcntl`/`lock` found only unrelated matches: `meta_agent.py` wall-clock guard, `grade.py` regex; the only `.lock` file is `.claude/scheduled_tasks.lock` in `.gitignore`, harness-owned). Concurrency is instead avoided by **path isolation**: every ticket gets its OWN worktree at `.worktrees/<id>/`, and all per-ticket runtime files (artifacts, the critic-metrics ledger) are written under that worktree's `.qrspi/<id>/`. Two tickets therefore never target the same file today. **However**, within a SINGLE batch run, the orchestrator processes tickets **sequentially** in a `for` loop (one `switch`/`do*` per iteration), so even same-process concurrency is absent. The risk the question raises (two processes appending to one shared `events.jsonl` or racing rotation) would only arise if a NEW design puts the event log at a **shared, non-worktree-scoped path** (e.g. repo-root `.qrspi/observability/events.jsonl`) AND multiple batch invocations run at once — neither of which the current code does or guards against.

**Evidence:**

```
const worktrees_dir = ...   // (Python) per-ticket isolation:
    worktrees_dir = os.path.join(repo_root, ".worktrees")
    worktree = os.path.join(worktrees_dir, ticket)
    if os.path.isdir(worktree):
        return worktree  # reuse
```

— `scripts/qrspi_resolve.py:434-438`

```
    for (let i = 0; i < tickets.length; i++) {   // sequential, one ticket per iteration
      ...
      switch (a) { ... }
```

— `.claude/workflows/qrspi-batch.js` per-ticket loop (`switch` at `:2678`)

**Dependencies:** Worktree provisioning is `qrspi_resolve.py:setup_worktree()`; per-ticket ledger path is `qrspi_metrics_append.py:ledger_path()` → `<root>/.worktrees/<id>/.qrspi/<id>/...`.
**Implicit contracts:** Per-ticket isolation is the de-facto concurrency model — "multiple agents [work] on different tickets concurrently" (CLAUDE.md Worktrees section) precisely because each is in its own worktree. **Gap to flag:** a shared event log breaks this assumption; there is zero existing lock/atomic-append machinery to build on. A worktree-scoped `events.jsonl` would inherit the existing isolation for free; a repo-root shared one would need new concurrency control.

## Q11: When log rotation fires at the size threshold mid-run, how is an in-flight append reconciled with the file being renamed/compressed, and where is the rotation trigger checked relative to each write?

**Answer:** **NOT FOUND — there is no log rotator, no size-threshold check, and no rotation/compression logic anywhere in the codebase.** Searches for rotation, size-threshold, compress/gzip, and archive returned nothing in `scripts/` or `.claude/workflows/`. The only append-style writer (`qrspi_metrics_append.py`) grows the per-ticket ledger unbounded with no size check before/after write. The proposed log rotator referenced in the question does not exist yet — it is entirely greenfield. There is therefore no existing answer to "where the rotation trigger is checked relative to each write" or "how an in-flight append is reconciled with a rename" — these are new design decisions with no codebase precedent to mirror. The nearest reusable idiom for safe file replacement is the write-temp-then-rename in `qrspi_clear_stale_pr.py:118` (whole-file, not rotation).

**Evidence:**

```
$ grep -rn "rotat\|threshold\|gzip\|compress\|archive\|getsize" scripts/*.py | grep -v _test
# (no rotation/threshold/compression matches; os.path.getsize used only for
#  non-empty verification in qrspi_persist.py / qrspi_metrics_append.py)
```

— search result, `scripts/` (rotation machinery absent)

**Dependencies:** None — feature does not exist.
**Implicit contracts:** N/A (greenfield). Note the existing append writer has no rotation hook, so a rotator must be inserted by the design either inside the appender or as a pre-write check; the codebase offers no established "check-then-write" rotation ordering to follow.

## Q12: What is the established unit-test pattern and runner the event emitter, log rotator, and retention cleaner tests must conform to?

**Answer:** Established pattern: a **stdlib-only `unittest`** `_test.py` sibling next to each script (`scripts/<name>.py` → `scripts/<name>_test.py`), importing the module directly (`import qrspi_persist as qp`), with pure helpers exercised against in-memory data and `tempfile.TemporaryDirectory()` for filesystem behavior. Each test file is standalone — runnable as `python3 scripts/<name>_test.py`, exiting 0/non-0. The aggregating runner `scripts/run_tests.py` discovers every `scripts/*_test.py`, runs each as its own subprocess (180s timeout), and exits non-zero if any fail. CI (`.github/workflows/tests.yml`) runs `python3 scripts/run_tests.py` (Python job) plus `node scripts/check_workflows.js .claude/workflows/*.js` (workflow-syntax job) on every PR and push to main. **No pytest, no third-party test deps** (`requirements.txt` lists only `anthropic`). The `qrspi_metrics_append_test.py` file is the direct template for a JSONL writer's tests (pure path/envelope helpers + temp-dir append/round-trip cases).

**Evidence:**

```
"""Stdlib-only unit tests for qrspi_persist.py. Run: python3 scripts/qrspi_persist_test.py"""
import os
import tempfile
import unittest
import qrspi_persist as qp
```

— `scripts/qrspi_persist_test.py:1-6`

```
def discover_tests(scripts_dir=SCRIPT_DIR, pattern=None):
    """Return the sorted absolute paths of every ``*_test.py`` in *scripts_dir*."""
    names = sorted(n for n in os.listdir(scripts_dir) if n.endswith("_test.py"))
```

— `scripts/run_tests.py:36-45`

**Dependencies:** `run_tests.py` (runner) → each `*_test.py` (subprocess). CI: `.github/workflows/tests.yml` → `run_tests.py` + `check_workflows.js`.
**Implicit contracts:** Test files MUST end in `_test.py` to be discovered. Tests MUST be stdlib-only (CI has no dependency-install step — `tests.yml:34-35`). Tests import the module by name (so `sys.path` includes `scripts/` when run from there — the import is bare `import qrspi_X`). New emitter/rotator/cleaner tests must each be a `scripts/qrspi_<thing>_test.py` sibling, stdlib-only, temp-dir based, self-exiting.

## Q13: Where would a JSON schema file enforcing the event schema live, and is there any existing schema-validation utility or dependency the tests could use to validate emitted events against it?

**Answer:** **NOT FOUND — no JSON schema files and no `jsonschema` dependency exist.** A repo-wide search for `*schema*.json` files returned nothing; `requirements.txt` lists only `anthropic==0.49.0` (no `jsonschema`). The word "schema" in the codebase refers to **JS-object literal schemas** inside `qrspi-batch.js` (`TICKETS_SCHEMA`, `CRITIC_VERDICT_SCHEMA`, `PERSIST_SCHEMA`, etc.) consumed by the harness's `agent({ schema })` StructuredOutput validation — these are inline JS objects, not JSON Schema files, and validation is done by the Claude Code harness, not a Python library. Python "validation" today is hand-rolled type/shape checks (e.g. `qrspi_metrics_append.py` checks `isinstance(record, dict)`; `qrspi_critics_config.py` does per-field type guards). So enforcing an event schema in tests would require either (a) adding a `jsonschema` dependency (breaking the stdlib-only CI contract — see Q12), or (b) hand-rolled stdlib validation matching the existing `isinstance`/type-guard convention. A schema file, if added, has no established home; the only schema-ish committed assets are `.qrspi/templates/` (markdown artifact templates) and `config.example.json`.

**Evidence:**

```
$ cat scripts/requirements.txt
anthropic==0.49.0
```

— `scripts/requirements.txt` (no jsonschema; stdlib-only test contract)

```
const TICKETS_SCHEMA = {
  type: 'object',
  required: ['tickets'],
  properties: { tickets: { type: 'array', items: { ... } } },
}
```

— `.claude/workflows/qrspi-batch.js:182-200` (schemas are inline JS objects for the harness, not JSON Schema files)

**Dependencies:** JS schemas → harness `agent({ schema })` StructuredOutput. Python shape checks are inline per-script.
**Implicit contracts:** Tests are stdlib-only (Q12) — adding `jsonschema` would break CI's no-install assumption (`tests.yml:34-35`) and the documented "stdlib-only unit tests" rule (CLAUDE.md). The established validation idiom is hand-rolled `isinstance`/type guards with fail-closed behavior. Any event-schema enforcement should therefore most likely be stdlib hand-rolled (or accept a new dependency as an explicit design tradeoff).

## Q14: What logging or event-emission mechanism, if any, exists in the pipeline today, and how does it interact with interactive vs. non-interactive (batch) runs that the CLI stderr requirement distinguishes?

**Answer:** Two distinct mechanisms exist; neither is a structured event log. (1) **Human-readable progress logging** via the harness-provided `log()` and `phase()` globals in `qrspi-batch.js` — these are NOT defined in the file (no `function log` / `const log`); they are injected by the Workflow runner and emit free-text progress lines (e.g. ``log(`  ${id}: ${name} → saved ${p.bytes}B`)``). The orchestrator has no notion of stdout-vs-stderr or interactive-vs-batch routing — it just calls `log()`. (2) **The critic-metrics JSONL ledger** (`qrspi_metrics_append.py`) — the ONLY durable, machine-readable per-step record today, written one JSON line per terminated critic step into `.qrspi/<id>/critic-metrics.jsonl`, summarizable by run via `runId`. The Python scripts themselves emit a single JSON envelope to **stdout** (e.g. `json.dump(env, sys.stdout)`); errors are returned **in that JSON envelope** (`ok:false`, verbatim `error`), not written to stderr. The eval/grade harness prints progress to stdout/stderr ad hoc. **There is no interactive-vs-non-interactive distinction anywhere** — no code branches on TTY/`isatty`, and no stderr-vs-stdout policy. The CLI's "stderr for logs" requirement has no existing precedent to inherit.

**Evidence:**

```
  log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
  return true
```

— `.claude/workflows/qrspi-batch.js:1359-1360` (`log` is an injected harness global, undefined in-file)

```
    env["error"] = error
    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if error is None else 1
```

— `scripts/qrspi_persist.py:128-133` (Python tools: JSON envelope to stdout; errors in-band, not stderr)

**Dependencies:** `log()`/`phase()` are Workflow-runner globals. The metrics ledger: orchestrator shell-out (`.claude/workflows/qrspi-batch.js:980`) → `qrspi_metrics_append.py` → per-ticket `.jsonl`. `runId` scopes ledger lines for `qrspi_critic_summary.py`.
**Implicit contracts:** Python tools speak JSON-on-stdout with in-band `ok`/`error` (NOT stderr) and exit codes — a new logger writing logs to stderr would be a NEW convention diverging from the existing stdout-JSON pattern (must not pollute the stdout JSON envelope the orchestrator parses). The existing JSONL ledger (`qrspi_metrics_append.py`) is the single closest precedent for a structured `events.jsonl` emitter and should be the design's reference implementation.

---

## Discovered Patterns

- **Self-locating, stdlib-only Python tools.** Every `scripts/qrspi_*.py` derives its root from `__file__` (or `qrspi_paths.resolve_repo_root()` for worktree-correctness), takes short token-free args, prints a single JSON envelope to stdout, exits 0/non-0, fails closed, and has a `_test.py` sibling. `qrspi_persist.py` and `qrspi_metrics_append.py` are the canonical models.
- **Fail-closed everywhere.** Reads default to `{}` on error and never raise (`qrspi_config.read_config`); writes verify non-empty after and return an error if not; malformed input exits non-zero writing nothing. A new emitter is expected to follow this.
- **Path isolation as the concurrency model.** Per-ticket worktrees (`.worktrees/<id>/`) plus per-ticket `.qrspi/<id>/` sinks mean no shared mutable file exists today; the batch loop is sequential. No locks anywhere.
- **JS sandbox cannot do I/O or run Python** — it delegates via `agent()` worker prompts and shell-outs through `engineCmd('scripts/...')`. Any JS-layer event emission must shell out to a Python helper.
- **Resume-safe id generation.** `Date.now()`/`Math.random()` are forbidden in workflow scripts; ids use crypto with guarded fallbacks (`runId`).
- **The critic-metrics JSONL ledger is the lone structured-record precedent** (`qrspi_metrics_append.py`): one JSON line per record, `runId`+`ticketId`+`timestamp` envelope, per-ticket `.jsonl`, run-scoped summarization. It is the obvious reference for an `events.jsonl` emitter.
- **Config is single-flat-key by default** (`qrspi_config.py`); the one nested block (`critics.*`) has a purpose-built resolver (`qrspi_critics_config.py`) rather than a generic dot-path reader.

## Inconsistencies

- **Ticket premise vs. code (Q7):** the ticket assumes an "exponential-backoff retry policy already defined in the pipeline config." No such policy exists. The pipeline has a consecutive-red CI **cap counter** (no delay/backoff seconds), and the only real exponential backoff lives in the *eval* harness (`grade.py`, module constants, not config). `backoff_seconds` has no source in the phase pipeline; `retry_attempt` could only map to the `CI-Revise-Attempt` trailer.
- **Ticket premise vs. code (Q9/Q11):** "single-line, flushed-before-continue writes" and "log rotation" / crash-safety are described as if present. There is no flush/fsync (relies on context-manager close), no atomic-append guarantee, no rotation/threshold/compression code at all. These are greenfield, not extensions of existing behavior.
- **Ticket premise vs. code (Q14):** an interactive-vs-non-interactive / stderr-for-logs distinction is implied. No code branches on TTY, and Python tools emit JSON+errors to **stdout** (in-band), not stderr — so a stderr logging policy is a new, slightly conflicting convention that must avoid corrupting the stdout JSON envelopes the orchestrator parses.
- **Phase-name casing split:** machine phase names are lowercase (`design`/`plan`/`implementation`) in the resolver envelope, but display/`phase()` labels are Titlecase (`Design`/`Plan`/...). An event `phase` field must choose and map deliberately.
- **`.qrspi/` gitignore is selective:** only `config.json` and `features/` (and `.worktrees/`) are ignored, NOT `.qrspi/` broadly. A repo-root `.qrspi/observability/` would be git-tracked unless a new `.gitignore` entry is added — easy to overlook given the per-ticket `.qrspi/<id>/` dirs live inside the already-ignored `.worktrees/` tree.
- **Schema vocabulary collision:** "schema" in-repo means inline JS StructuredOutput objects validated by the harness, not JSON Schema files; there is no `jsonschema` dep and CI is stdlib-only, so file-based schema validation in tests would conflict with the no-dependency contract.
