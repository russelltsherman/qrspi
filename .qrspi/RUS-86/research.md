# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Q1: Where in the batch loop does each phase transition occur today (start, end, success, failure, retry), and what value carries the active span's id so the orchestrator can thread it as `parent_span_id` into nested events?

**Answer:** There is NO span/trace concept in the codebase today — no `parent_span_id`, no span id, no nesting context. Phase transitions are signalled by two injected globals that are NOT defined in the file: `phase(<label>)` (a harness-provided phase marker) and `log(<string>)` (a harness-provided line logger). The per-ticket loop dispatches actions through a `switch` on `r.decision.action` (`.claude/workflows/qrspi-batch.js:2678-2696`). Each handler (`doDesign`, `doPlan`, `doImplementation`, `doSubmit`, `doReset`, `doRevise`, `doLand`) calls `phase('Finalize')`/`phase('Resolve')`/etc. at its start, then `log(...)` lines for progress, and returns a result object pushed to `results`. Success vs failure is a per-handler boolean/`null` from `agent(...)` (e.g. `runPhase` returns `false` on failure, `.claude/workflows/qrspi-batch.js:1296-1360`). "Retry" is not a loop construct — the only retry-ish concept is the CI-revise counter (`CI-Revise-Attempt` trailer), addressed in Q7/Q9. The closest existing "run-scoped correlation id" is `runId` (Q2), the only value threaded into nested events today (the critic-metrics ledger lines).
**Evidence:**

```
const a = r.decision.action
log(`  ${t.id}: decision=${a} — ${r.decision.reason}`)
let res
switch (a) {
  case 'run_design': res = await doDesign(t, r); break
  case 'advance': ...
  case 'submit': res = await doSubmit(t, r); break
  case 'revise': res = await doRevise(t, r); break
  case 'land': res = await doLand(t, r); break
  ...
}
results.push(res)
```

— `.claude/workflows/qrspi-batch.js:2675-2697`
**Dependencies:** `phase()` and `log()` are injected harness globals (no `const`/`function` definition exists in the file — grep for `const log`/`function log` finds none). `agent()` is the injected subagent-spawn primitive. Downstream: `results[]` array, returned at the end of the run.
**Implicit contracts:** Phase handlers must return a result object carrying at least `{ ticketId, action, summary }` (see `skip()` at `.claude/workflows/qrspi-batch.js:635-643`). There is no span/parent context to thread; an observability event log would have to invent one. `runId` is the only existing run-scoped id and is already passed into nested writes (Q2).

## Q2: How is the per-invocation `runId` currently generated and propagated, and from where would the emitter read it to populate `context.run_id`?

**Answer:** `runId` is a single module-level `const` computed ONCE at the top of the imperative shell. Precedence: `process.env.QRSPI_RUN_ID` (harness-exported) → `crypto.randomUUID()` → a `crypto.getRandomValues`-derived `run-<hex>` → the constant `'run-fallback'`. Workflow scripts forbid `Date.now()`/`Math.random()` (they break resume), so no timestamp/Math.random path exists. It is propagated by string-interpolation into worker prompts — concretely into the `qrspi_metrics_append.py` invocation via `--run-id '${runId}'` (`.claude/workflows/qrspi-batch.js:980`). An event emitter would read this same `runId` const directly (it is in module scope) to populate `context.run_id`.
**Evidence:**

```
const runId =
  (typeof process !== 'undefined' && process.env && process.env.QRSPI_RUN_ID) ||
  (typeof crypto !== 'undefined' && crypto.randomUUID && crypto.randomUUID()) ||
  (typeof crypto !== 'undefined' &&
    crypto.getRandomValues &&
    `run-${Array.from(crypto.getRandomValues(new Uint8Array(8)))
      .map((b) => b.toString(16).padStart(2, '0')).join('')}`) ||
  'run-fallback'
```

— `.claude/workflows/qrspi-batch.js:118-126`
**Dependencies:** `process.env.QRSPI_RUN_ID` (optional harness env var); `crypto` (web/node global). Consumer today: the metrics-append shell-out (`--run-id '${runId}'`, `.claude/workflows/qrspi-batch.js:980`), which stamps it onto each `CriticMetricsLedgerLine` as the string field `runId` (`scripts/qrspi_metrics_append.py:67-79`).
**Implicit contracts:** "runId always present, always a string" — the appender requires `--run-id` (`required=True`, `scripts/qrspi_metrics_append.py:111-113`). Project memory `qrspi-batch-runid-datenow-bug.md` documents that the fallback MUST NOT use `Date.now()`/`Math.random()` (breaks workflow resume); any new emitter must honor that.

## Q3: How is the main checkout's repo root located today (versus the worktree path), so the per-ticket event file can be written to `.qrspi/observability/<ticket_id>.events.jsonl` in the main checkout rather than inside the worktree?

**Answer:** The single source of truth is `qrspi_paths.resolve_repo_root(repo_root=None, cwd=None, validate=True)` (`scripts/qrspi_paths.py:111-143`). Precedence: explicit `--repo-root` (validated) → `git rev-parse --path-format=absolute --git-common-dir` then `dirname` (the SHARED `.git`, i.e. the MAIN checkout even from a linked worktree) → `__file__`-parent fallback. Validation runs `gh repo view` and raises `HostRootError` on mismatch. Scripts that write into the host (e.g. `qrspi_metrics_append.py`) call it with `validate=False` (keeps `gh` off the import path), then compute host paths off the resolved root. The worktree path for a ticket is computed separately as `<root>/.worktrees/<ticket>` (e.g. `qrspi_ci_revise_bump.worktree_path`, `scripts/qrspi_ci_revise_bump.py:69-72`). So an observability file in the MAIN checkout would be `os.path.join(resolve_repo_root(...), ".qrspi", "observability", "<id>.events.jsonl")` — note the existing metrics ledger does the OPPOSITE (writes INTO the worktree at `<root>/.worktrees/<id>/.qrspi/<id>/...`, see Q15), so writing to the main checkout's `.qrspi/` directly is a NEW path shape not yet used.
**Evidence:**

```
def _git_common_dir(cwd=None):
    res = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=cwd, capture_output=True, text=True)
    ...
    common = (res.stdout or "").strip()
    if res.returncode == 0 and common:
        return os.path.dirname(common)
    return None
```

— `scripts/qrspi_paths.py:57-78`
**Dependencies:** `git rev-parse` (CLI), optional `gh repo view` validation. Consumers: `qrspi_metrics_append.py:131`, `qrspi_cleanup.py:58`, `qrspi_ci_revise_bump.py:59/215`, `qrspi_persist.py`, `qrspi_resolve.py`.
**Implicit contracts:** Engine-vs-host split (`engine_root()` for `sys.path` imports; `resolve_repo_root()` for host paths). A worktree-invoked script that self-located from `__file__` would yield the WORKTREE root and double-nest (`.worktrees/<id>/.worktrees/<id>/...`) — the exact failure `resolve_repo_root` exists to prevent (`scripts/qrspi_metrics_append.py:20-28`). `validate=False` is the convention for write-side scripts so they don't shell out to `gh` on import.

## Q4: What is the existing convention for an importable, self-locating stdlib-only Python module in this repo (signatures, no third-party deps), that a shared logger module would follow?

**Answer:** Established and consistent across `scripts/`. Conventions: (1) `#!/usr/bin/env python3` shebang + module docstring explaining "Why this exists"; (2) stdlib-only imports (`argparse`, `json`, `os`, `re`, `subprocess`, `sys`, `datetime`); (3) `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))` then `sys.path.insert(0, ENGINE_ROOT)` for sibling imports; (4) host root via `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)`; (5) PURE helpers separated under a `# --- pure helpers (unit-tested) ---` banner from `# --- subprocess-backed mechanics (not unit-tested) ---`; (6) a `main()` that parses args, emits ONE JSON envelope to stdout via `json.dump(env, sys.stdout, indent=2); print()`, and `sys.exit(0/1)`; (7) a `_test.py` sibling. `qrspi_config.py` is the simplest model (read one config key, print `{ok, key, value}`); `qrspi_metrics_append.py` is the model for a write-side, self-locating, fail-closed appender.
**Evidence:**

```
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)

import qrspi_paths  # noqa: E402
...
REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)
```

— `scripts/qrspi_metrics_append.py:52-58` (identical pattern at `qrspi_cleanup.py:45-58`, `qrspi_ci_revise_bump.py:54-59`)
**Dependencies:** `qrspi_paths` (sibling), Python stdlib only. `scripts/requirements.txt` exists but the harness scripts are stdlib-only by rule (CLAUDE.md: "stdlib-only unit tests").
**Implicit contracts:** Pure functions take args + return values (no I/O) so the `_test.py` can exercise them with in-memory data (`scripts/qrspi_config.py:36-42`). The single-JSON-envelope-on-stdout + exit-code contract is how the JS orchestrator consumes the script (Q5). A logger module would follow the importable-pure-core + thin-CLI split.

## Q5: How does the JS orchestrator currently shell out to Python scripts and consume their output, which determines how `qrspi-batch.js` would invoke or call the new event emitter / logger?

**Answer:** The orchestrator NEVER runs Python directly (no `child_process`/`execFileSync`/`spawnSync` — grep finds none). It spawns a subagent via `agent(prompt, opts)` whose prompt instructs the worker to "Run EXACTLY this one command verbatim": `python3 ${engineCmd('scripts/...')} ...` (for main-repo-cwd workers) or `python3 ${engineCmdFor(r, 'scripts/...')} ...` (for worktree-cwd workers). The worker runs the command and returns the script's JSON stdout, which the orchestrator parses with a `parse*Envelope` JS function (text → `extractJsonObject` → `JSON.parse` → field validation). `engineCmd(rel)` = `${ENGINE_ROOT}/${rel}` (ENGINE_ROOT = `CLAUDE_PLUGIN_ROOT` || `process.cwd()` || `.`); `engineCmdFor(r, rel)` anchors on the host root derived from `r.worktreeDir` so a worker running inside a worktree still finds the engine scripts. For pipe-in, the pattern is `printf '%s' ${JSON.stringify(...)} | python3 ${engineCmd('scripts/...')}`.
**Evidence:**

```
const engineCmd = (rel) => `${ENGINE_ROOT}/${rel}`
...
const engineCmdFor = (r, rel) => `${engineRootFor(r)}/${rel}`
```

— `.claude/workflows/qrspi-batch.js:76, 105`; representative shell-out: the metrics pipeline at `.claude/workflows/qrspi-batch.js:980` (`printf ... | python3 ${engineCmd('scripts/qrspi_critic_metrics.py')} ... | tee ... && python3 ${engineCmd('scripts/qrspi_metrics_append.py')} --ticket ${id} --run-id '${runId}' --record "$(cat ...)" ...`)
**Dependencies:** injected `agent()` global; the `parse*Envelope` JS helpers (`parseConfigEnvelope` at `:366`, `parseResolveEnvelope`, etc.); `extractJsonObject` brace-scanner (`.claude/workflows/qrspi-batch.js:222-258`).
**Implicit contracts:** A worker's reliability is weak — the orchestrator wraps every shell-out in "no path edits, no exploration, no alternatives, HARD STOP on ok:false" language and validates the echoed JSON defensively (a garbled echo becomes a clean `ok:false`). `engineCmdFor(r,...)` MUST be used for worktree-cwd workers (a bare `.` re-resolves against the worktree, missing relocated scripts — see `engineCmdFor` doc `.claude/workflows/qrspi-batch.js:78-105` and project memory `batch-worker-cwd-engine-path.md`). A new emitter invoked from JS would follow the same `agent()` + verbatim-command + parse-envelope shape; if invoked from a worker's main cwd use `engineCmd`, from a worktree use `engineCmdFor(r, ...)`.

## Q6: What config keys does the config reader expose and by what access mechanism (single top-level key vs nested dot-path), given the ticket adds a nested `observability.*` block plus top-level `ciReviseBackoffBase`/`ciReviseBackoffCap`?

**Answer:** The reader is SINGLE-TOP-LEVEL-KEY ONLY — there is NO dot-path / nested access. Two layers: (1) `qrspi_config.py` CLI `--key <name>` returns `{ok, key, value}` where `value` is the truthy config value or a per-key default; only `linearProject` has a default (`"QRSPI"`); unknown keys default to `""`. `select_value` returns `config.get(key)` (no traversal). (2) Python callers that need a key bypass the CLI and call `qrspi_config.read_config(repo_root)` → a flat dict, then `config.get("<flatKey>")` (e.g. `load_ci_revise_cap` reads `config.get("ciReviseCap")`, `scripts/qrspi_resolve.py:405-411`). (3) The JS `parseConfigEnvelope(text, key)` validates the CLI envelope and REJECTS a non-string `value` (`typeof env.value !== 'string'` → ok:false, `.claude/workflows/qrspi-batch.js:374`). Consequence: a nested `observability.*` block CANNOT be read by the existing `--key`/`read_config().get()` path — it would need either a new reader (dot-path or a dedicated `read_observability_config()` helper) or the block flattened. Top-level `ciReviseBackoffBase`/`ciReviseBackoffCap` would read fine via `read_config().get(...)` (like `ciReviseCap`), but NOT via the JS `parseConfigEnvelope` if the value is a number (it requires a string).
**Evidence:**

```
def select_value(config: dict, key: str, default: str) -> str:
    value = config.get(key)
    return value if value else default
```

— `scripts/qrspi_config.py:36-42`; flat-key consumer: `scripts/qrspi_resolve.py:405-411` (`config.get("ciReviseCap")`); JS string-only gate: `.claude/workflows/qrspi-batch.js:374`
**Dependencies:** `.qrspi/config.json` (gitignored; `.qrspi/config.example.json` is the template). Consumers: JS `parseConfigEnvelope` (Query scope), `load_ci_revise_cap`/`coerce_cap` (resolver cap).
**Implicit contracts:** Project memory `qrspi-config-reader-single-key-only.md` is explicit: "reads one top-level key (no dot-path); JS parseConfigEnvelope rejects non-string values; plans must specify nested-config read mechanism." `coerce_cap` shows the existing pattern for a NUMERIC top-level key: read via `read_config().get(...)` (a Python int), coerce defensively, reject `bool` (`scripts/qrspi_resolve.py:393-402`) — a backoff base/cap would mirror this, NOT go through the string-only CLI envelope.

## Q7: How does the resolver currently read the `CI-Revise-Attempt` trailer and the head commit's `committedDate`, the two inputs the backoff gate needs to compute elapsed time since the last attempt?

**Answer:** The `CI-Revise-Attempt` trailer IS read; `committedDate` is NOT fetched at all today — this is a gap the backoff gate must close. (1) Trailer: the gather's GraphQL fetches the head commit `message` (`commits(last:1){nodes{commit{message ...}}}`, `scripts/qrspi_pr_state.py:47-50`), and `ci_revise_attempt(message)` parses `^CI-Revise-Attempt:\s*(\d+)\s*$` (MULTILINE, last-occurrence wins, absent→0, `scripts/qrspi_pr_state.py:112-130`). The EFFECTIVE counter is forced to 0 whenever `ciState != "red"` (the not-red→0 read-side reset, `scripts/qrspi_pr_state.py:303-307`) and surfaced as `ciReviseAttempt` on the parsed PR node. The resolver reads it via `ci_revise_attempt_of` (`scripts/qrspi_resolve_state.py:129-138`). (2) `committedDate`: the GraphQL query (`PR_QUERY`, `scripts/qrspi_pr_state.py:26-69`) fetches `message` and `statusCheckRollup` on the head commit but NOT `committedDate`/`authoredDate`/`pushedDate` (grep confirms zero matches). So there is NO elapsed-time input anywhere — the resolver is fully time-agnostic today (no `datetime.now`, `time.time`, `monotonic`, or clock anywhere in `qrspi_resolve_state.py`).
**Evidence:**

```
        commits(last:1) {
          nodes {
            commit {
              message
              statusCheckRollup {
                state
                contexts(first:100) { ... }
```

— `scripts/qrspi_pr_state.py:47-53` (note: NO `committedDate` field selected)

```
def ci_revise_attempt(message):
    matches = _CI_REVISE_ATTEMPT_RE.findall(message or "")
    if not matches:
        return 0
    try:
        return int(matches[-1])
    except (TypeError, ValueError):
        return 0
```

— `scripts/qrspi_pr_state.py:115-130`
**Dependencies:** `gh api graphql` (the head-commit query). The trailer is the shared serialization contract between the writer (`qrspi_ci_revise_bump.py`) and the reader (`qrspi_pr_state.ci_revise_attempt`) — identical regex in both (`scripts/qrspi_ci_revise_bump.py:64-88`).
**Implicit contracts:** The trailer parse semantics MUST stay byte-identical between writer and reader (last-occurrence-wins, absent→0). The resolver `resolve(state, ci_revise_cap=3)` is PURE — no clock, no I/O (`scripts/qrspi_resolve_state.py:173-181`); adding elapsed-time would require the GATHER to fetch `committedDate` and pass it (plus a "now" / clock value) INTO the pure resolver as data, preserving purity — there is no precedent for an injected clock in the resolver yet (see Q11).

## Q8: Where does the resolver evaluate the CI precedence slot (after unified-feedback, before active-phase) that the new backoff gate must sit within to turn a still-red frontier into `wait`?

**Answer:** Step "2c. CI-gated revise/wait" in `resolve()`, `scripts/qrspi_resolve_state.py:274-307`. It runs AFTER the unified-feedback handler (step 2b, `:240-272`) and BEFORE the active-phase block (step 3, `:309+`). It evaluates ONLY the FRONTIER (highest existing) phase: `frontier = max(existing, key=_order); fci = ci_state(phases, frontier)`. Logic: `red` + `attempt < cap` → `revise` (`ciFailing=True`); `red` + `attempt >= cap` → `wait` (`ciFailing=True, ciGaveUp=True`) — the existing cap-then-wait; `pending` → `wait`; `green`/`none` → fall through. The backoff gate would insert a NEW condition in the `red` branch: when the trailer count is >0 AND elapsed-since-last-attempt < backoff window, return `wait` instead of `revise` (spacing retries), composing with — and BEFORE/within — the existing cap check.
**Evidence:**

```
    frontier = max(existing, key=_order)
    fci = ci_state(phases, frontier)
    if fci == "red":
        attempt = ci_revise_attempt_of(phases, frontier)
        if attempt < ci_revise_cap:
            return decision("revise", phase=frontier, ciFailing=True, ...)
        return decision("wait", phase=frontier, ciFailing=True, ciGaveUp=True, ...)
    if fci == "pending":
        return decision("wait", phase=frontier, ...)
```

— `scripts/qrspi_resolve_state.py:288-307`
**Dependencies:** `ci_state()` (`:110-126`), `ci_revise_attempt_of()` (`:129-138`), the `decision()` factory (`:185-198`) whose fixed key set is `action, phase, nextPhase, resetToPhase, discardPhases, commentTargets, changeRequested, ciFailing, ciGaveUp, reason`.
**Implicit contracts:** The `decision` dict has a FIXED key set (`scripts/qrspi_resolve_state.py:185-198`) — adding a backoff signal (e.g. a "parked for backoff" flag) means adding a key here and re-emitting it at the envelope top level (mirroring `ciFailing`/`ciRedBranches` in `qrspi_resolve.py`, Q9). A non-frontier red PR takes NO CI action (comment at `:280-282`). The frontier-only rule and the "red is fixed before advance builds the next phase" precedence must be preserved.

## Q9: How is the consecutive-red cap (`ciReviseCap`) read, defaulted, and its two resets implemented today, so the new backoff spacing composes with the existing bounding without conflict?

**Answer:** READ: `load_ci_revise_cap(repo_root)` → `qrspi_config.read_config()` → `config.get("ciReviseCap")` → `coerce_cap()` (single flat top-level key; `scripts/qrspi_resolve.py:405-411`). DEFAULT: `coerce_cap` returns `3` for anything not a positive int — rejects `bool` explicitly, rejects floats/strings/None/non-positive (`scripts/qrspi_resolve.py:393-402`). The resolved cap is passed INTO the pure resolver: `resolve(state, ci_revise_cap=cap)` (`scripts/qrspi_resolve.py:506-507`); the resolver default is also `3` (`scripts/qrspi_resolve_state.py:173`). TWO RESETS: (1) READ-SIDE in the gather — `ciReviseAttempt` forced to 0 whenever `ciState != "red"` (`scripts/qrspi_pr_state.py:303-307`); (2) WRITER-SIDE in `doRevise` — `bumpCiReviseTrailers` writes `<prior+1>` on the CI path (`.claude/workflows/qrspi-batch.js:2217-2243`), and `resetCiReviseTrailer` overwrites to 0 on every non-CI amend (called at `:1998` for comment-applies, and on the green-CI change-request path). The deterministic +1 lives in `qrspi_ci_revise_bump.bump_ci_revise_trailer` (`scripts/qrspi_ci_revise_bump.py:91-118`).
**Evidence:**

```
def coerce_cap(value):
    if isinstance(value, bool) or not isinstance(value, int):
        return CI_REVISE_CAP_DEFAULT
    return value if value > 0 else CI_REVISE_CAP_DEFAULT

def load_ci_revise_cap(repo_root=REPO_ROOT):
    config = qrspi_config.read_config(repo_root)
    return coerce_cap(config.get("ciReviseCap"))
```

— `scripts/qrspi_resolve.py:393-411`
**Dependencies:** `qrspi_config.read_config`, the resolver `resolve(...)`, the gather's not-red→0 normalization, the JS `bumpCiReviseTrailers`/`resetCiReviseTrailer`.
**Implicit contracts:** The trailer is the durable, GitHub-observable counter (Decision 2 Option C per the bump docstring). The not-red→0 read-side reset means the EFFECTIVE attempt count the resolver sees is 0 unless the frontier is currently red — a backoff gate keying off the trailer must reckon with this (the trailer on the commit may be >0 but the effective field is 0 once CI flips green). Two new flat config keys (`ciReviseBackoffBase`/`ciReviseBackoffCap`) would follow the `coerce_cap`/`load_ci_revise_cap` numeric pattern, NOT the string-only CLI envelope. The backoff must compose so the cap still terminates the loop (cap is the hard stop; backoff only spaces retries below the cap).

## Q10: How is worktree teardown performed, and what paths does it remove, to confirm a file under `.qrspi/observability/` in the main checkout survives cleanup?

**Answer:** Teardown is `qrspi_cleanup.py`, gated by the pure `classify_cleanup` (blocked > destroy > skip; only a fully-merged clean stack is destroyed). On `destroy` it removes EXACTLY: (1) the worktree dir via `git worktree remove --force <root>/.worktrees/<id>` (`scripts/qrspi_cleanup.py:168-180`); (2) local stack branches `<id>/design|plan|slice-*` via `git branch -D` (`:183-196`); (3) merged remote `<id>/*` refs via `gt sync --force` (`:225-288`). It NEVER touches `<root>/.qrspi/` in the MAIN checkout — only `<root>/.worktrees/<id>` and `<id>/*` branches/refs. A file at `<root>/.qrspi/observability/<id>.events.jsonl` (main checkout, OUTSIDE `.worktrees/`) SURVIVES cleanup. CAVEAT: the EXISTING metrics ledger is written INSIDE the worktree (`<root>/.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`, Q15), so it is DESTROYED with the worktree — confirming that to survive, the observability file must live in the main checkout's `.qrspi/`, not the worktree's.
**Evidence:**

```
def _remove_worktree(wt_path, dry_run):
    if not os.path.isdir(wt_path):
        return False
    ...
    rc, out, err = _run(["git", "worktree", "remove", "--force", wt_path], cwd=REPO_ROOT)
```

— `scripts/qrspi_cleanup.py:168-180`; `wt_path = worktree_path(REPO_ROOT, ticket)` = `<root>/.worktrees/<id>` (`:327`, via `qrspi_restack.worktree_path`)
**Dependencies:** `git worktree remove`, `git branch -D`, `gt sync --force`; `classify_cleanup` (pure). `worktree_path(REPO_ROOT, ticket)` from `qrspi_restack`.
**Implicit contracts:** Idempotent (missing worktree/branch/ref = clean no-op). A dirty worktree → `blocked`, never destroyed (`scripts/qrspi_cleanup.py:80-84`). The cleanup is scoped strictly to `<id>/*` namespaced refs and the single `.worktrees/<id>` dir — nothing under the main `.qrspi/` is in its removal set, so a main-checkout observability file is durable across teardown. (The reconciliation pass `runReconciliation` calls the SAME `qrspi_cleanup.py`, so this holds there too.)

## Q11: What is the existing pattern (if any) for injecting a clock into a resolver unit test, required to test the backoff gate's elapsed-time computation deterministically?

**Answer:** NO clock-injection pattern exists in the resolver or its test — `resolve()` is purely time-agnostic (no `datetime`/`time`/`monotonic`/`clock`; grep finds none in `qrspi_resolve_state.py` or its test). The resolver test (`qrspi_resolve_state_test.py`) is a stdlib-only, assert-based, table-driven suite: `_phase`/`_impl`/`_slice` factory builders produce in-memory state dicts (note they already accept `ci_state=`/`ci_attempt=` kwargs, `:14-35`), `state(...)` wraps them, and `CASES` collects `(name, state, expected)` tuples checked against `resolve(state)`. To inject elapsed time deterministically, the established repo precedents are: (a) PASS time as DATA into the pure function (like `ci_revise_cap` is passed in — `scripts/qrspi_resolve_state.py:173`), so the test supplies a fixed `now` + a fixed `committedDate`; or (b) MONKEYPATCH a module attribute in `setUp`/restore in `tearDown` — the exact pattern `qrspi_metrics_append_test.py` uses to pin `qrspi_paths.resolve_repo_root` (`:71-75`). Pattern (a) is strongly preferred here (keeps `resolve()` pure, matches the `ci_revise_cap` injection precedent).
**Evidence:**

```
def _phase(branch=True, pr=True, decision="REVIEW_REQUIRED", threads=0, comments=None,
           merged=False, ci_state="none", ci_attempt=0):
    return {"branchExists": branch, "prExists": pr,
            "reviewDecision": decision, "unresolvedThreads": threads,
            "commentTargets": comments or [], "merged": merged,
            "ciState": ci_state, "ciReviseAttempt": ci_attempt}
```

— `scripts/qrspi_resolve_state_test.py:14-19`; monkeypatch precedent: `scripts/qrspi_metrics_append_test.py:71-75`
**Dependencies:** `unittest`-free assert style in the resolver test (raw `assert`/`CASES`); `unittest.TestCase` + `setUp`/`tearDown` monkeypatch in the metrics-append test. No `freezegun`/`unittest.mock` third-party deps (stdlib-only rule).
**Implicit contracts:** Resolver purity is a hard invariant — `resolve()` "performs NO I/O of its own" (`scripts/qrspi_resolve_state.py:6-10`). The clock/elapsed value must therefore be a GATHERED input threaded in as data (the gather fetches `committedDate`, computes/passes a `now`), not read inside `resolve()`. The test factories must be extended (add `committed_date=` / `now=` kwargs) the same way `ci_state`/`ci_attempt` were added for RUS-81.

## Q12: Does the orchestrator currently write anything to stdout that downstream parses as JSON envelopes, which would be corrupted if the CLI logger emitted to stdout instead of stderr?

**Answer:** Two distinct stdout audiences exist; both matter. (1) The ORCHESTRATOR (`qrspi-batch.js`) does NOT write JSON to its own process stdout — it uses the injected `log()`/`phase()` harness globals (not `console.log`/`process.stdout`; the file's only `console.log`/`process.stdout` grep hits are in COMMENTS). Its result is the returned `results[]`/`reconciliation` value, consumed by the harness, not stdout-parsed. (2) The PYTHON SCRIPTS each emit ONE JSON envelope to THEIR stdout, which a worker echoes and the orchestrator parses (Q5). THIS is the fragile channel: any logger that writes to a Python script's stdout would interleave with the single-JSON-envelope contract and break `extractJsonObject`/`JSON.parse`. Several scripts already route diagnostics to stderr precisely for this reason (`qrspi_research_digest.py:104/109/116` use `sys.stderr.write`). So: a CLI logger MUST emit to stderr (or a file), never the script's stdout, to avoid corrupting the envelope the orchestrator parses.
**Evidence:**

```
json.dump(env, sys.stdout, indent=2)
print()
return 0 if error is None else 1
```

— `scripts/qrspi_metrics_append.py:147-149` (the one-envelope-on-stdout contract every script follows); stderr-for-diagnostics precedent: `scripts/qrspi_research_digest.py:104,109,116`
**Dependencies:** `extractJsonObject` (`.claude/workflows/qrspi-batch.js:222-258`) + `JSON.parse` in every `parse*Envelope`. The pipe pattern `... | tee /tmp/...json && python3 ... --record "$(cat ...)"` (`:980`) is especially brittle — extra stdout bytes would poison the captured record.
**Implicit contracts:** "Exactly one JSON envelope on stdout" is the universal script↔worker↔orchestrator contract. Diagnostics go to stderr. A shared logger that writes to a `cli.log` FILE (or stderr) is compatible; one that prints to stdout is NOT. The harness `log()`/`phase()` globals are separate from process stdout and safe.

## Q13: Is there any existing precedent in the codebase for atomic `O_APPEND` writes or a per-line size cap below `PIPE_BUF`, relevant to the `cli.log` shared-sink contention strategy?

**Answer:** NO precedent for `O_APPEND`/`os.open`/`fcntl`/`flock`/`PIPE_BUF`/per-line size caps anywhere in `scripts/` (grep finds none). The ONLY append-writer is `qrspi_metrics_append.append_line` (`scripts/qrspi_metrics_append.py:82-99`), which uses plain buffered `open(path, "a")` + `fh.write(json.dumps(...) + "\n")` — NO `os.open(..., O_APPEND)`, no lock, no size cap, no atomicity guarantee. It writes ONE line per process invocation (each metrics append is its own `python3` subprocess), and its concurrency assumption is implicit/serial: the orchestrator runs ticket actions SEQUENTIALLY (`.claude/workflows/qrspi-batch.js:2222-2223` notes "tickets share one .git index... must not race a sibling"), so contention has not been a concern. There is therefore NO existing pattern to reuse for a multi-writer `cli.log` shared sink — atomic `O_APPEND` + sub-`PIPE_BUF` line cap would be a NET-NEW mechanism for this repo.
**Evidence:**

```
def append_line(path, ledger_line):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(ledger_line) + "\n")
    try:
        size = os.path.getsize(path)
    ...
```

— `scripts/qrspi_metrics_append.py:82-99`
**Dependencies:** Python buffered text I/O only. Per-invocation, single-line writes; one ledger PER ticket (path `<root>/.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`), so today no two writers target the same file concurrently.
**Implicit contracts:** Fail-CLOSED: a write leaving the ledger empty returns an error (`:94-96`). One line per call, newline-terminated, JSON object. The "single ledger per ticket + sequential ticket processing" arrangement is what has made plain `open("a")` safe so far; a SHARED `cli.log` across tickets/phases would break that assumption and is the case the ticket's `O_APPEND`/`PIPE_BUF` strategy must newly handle — with no in-repo template.

## Q14: What is the existing test harness convention (`scripts/*_test.py`, stdlib-only, run via `scripts/run_tests.py`) that unit tests for the event emitter, log rotator, and retention cleaner must conform to?

**Answer:** `scripts/run_tests.py` discovers every `scripts/*_test.py` (basename suffix `_test.py`), runs each as its OWN `python3 <file>` subprocess (180s timeout), and exits non-zero if any fail (`scripts/run_tests.py:36-104`). Each test file MUST: be named `<module>_test.py`, be a standalone runnable that exits 0 on pass / non-zero on fail, be stdlib-only (no pytest/third-party). Two in-repo styles coexist and both work: (a) raw-assert + manual `CASES` table + a `__main__` runner returning an exit code (`qrspi_resolve_state_test.py`); (b) `unittest.TestCase` classes (`qrspi_metrics_append_test.py`) — note `unittest` self-reports exit code via `unittest.main()`. New tests for an emitter/rotator/cleaner would be `qrspi_<thing>_test.py` siblings, auto-discovered, run with `python3 scripts/run_tests.py [substring]`. CI gates on the same command (`.github/workflows/tests.yml`).
**Evidence:**

```
def discover_tests(scripts_dir=SCRIPT_DIR, pattern=None):
    names = sorted(n for n in os.listdir(scripts_dir) if n.endswith("_test.py"))
    if pattern:
        names = [n for n in names if pattern in n]
    return [os.path.join(scripts_dir, n) for n in names]
```

— `scripts/run_tests.py:36-48`; per-file subprocess at `:51-75`
**Dependencies:** `scripts/run_tests.py`, `.github/workflows/tests.yml` (CI gate per CLAUDE.md). Import convention: tests `from <module> import ...` directly (siblings on the same dir; the runner runs them with the scripts dir as cwd context).
**Implicit contracts:** Pure functions are the unit-test surface; subprocess/git/gh seams are NOT unit-tested (marked `# --- ... (not unit-tested) ---`). A test that needs the host root monkeypatches `qrspi_paths.resolve_repo_root` (`qrspi_metrics_append_test.py:71-75`) and uses `tempfile.TemporaryDirectory()` for filesystem effects. The runner must remain stdlib-only and exit-code-faithful so CI can gate.

## Q15: What logging or event-emission already exists in the pipeline (e.g. the fail-CLOSED metrics ledger referenced as the contrasting precedent), including its write/flush behavior and failure posture?

**Answer:** The existing precedent is the CRITIC-METRICS ledger (RUS-77/78): `qrspi_metrics_append.py`, a JSONL appender. Behavior: (1) pure reducer `qrspi_critic_metrics.build_record` produces a `CriticStepMetrics` record; (2) `qrspi_metrics_append.py` wraps it in a `CriticMetricsLedgerLine` envelope (injects `ticketId`, `timestamp` = UTC ISO-8601 at write time, `runId`) and APPENDS one JSON line. WRITE/FLUSH: plain `open(path, "a")` + `write(json.dumps(line) + "\n")`, implicit flush on context-exit; NO explicit fsync/lock. FAILURE POSTURE: FAIL-CLOSED — verifies the file is non-empty after write and returns an error (ok:false, exit 1) if the ledger is empty or unwritable; malformed `--record` JSON exits 1 writing nothing (`:116-129`). PATH: INSIDE the worktree — `<root>/.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl` (`ledger_path`, `:60-64`) — so it is destroyed by cleanup (contrast with Q10). Wired from JS via the metrics pipeline at `.claude/workflows/qrspi-batch.js:980`. This is the "fail-CLOSED metrics ledger" the ticket contrasts against (presumably the new observability log is fail-OPEN / best-effort so logging never blocks work).
**Evidence:**

```
def append_line(path, ledger_line):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(ledger_line) + "\n")
    ...
    if size == 0:
        return 0, 0, "ledger is empty after append: %s" % path
```

— `scripts/qrspi_metrics_append.py:82-96`; envelope injection `wrap_envelope` `:67-79`; in-worktree path `ledger_path` `:60-64`
**Dependencies:** `qrspi_critic_metrics.build_record` (pure reducer), `qrspi_paths.resolve_repo_root`, `runId` (Q2). Read-side consumer: `qrspi_critic_summary.py` (scopes a base-rate report to one `runId`). The JS wiring (`runCriticPanelLoop` → `criticConfig.criticMetrics`) at `.claude/workflows/qrspi-batch.js:1345-1349, 980`.
**Implicit contracts:** One JSONL line per terminated critic step; the appender is the SINGLE envelope authority (its `ticketId`/`timestamp`/`runId` win over any in the record). FAIL-CLOSED is deliberate for metrics (a lost metric is a real gap). NOTE the design contrast the ticket likely draws: this ledger is fail-CLOSED and lives in the worktree (destroyed on cleanup); a per-ticket OBSERVABILITY event log would presumably be fail-OPEN (best-effort, never blocks the run — matching the "Linear write never blocks work" posture in CLAUDE.md) and live in the MAIN checkout `.qrspi/observability/` to survive teardown.

---

## Discovered Patterns

- **Self-locating script triad**: every host-mutating script does `ENGINE_ROOT = dirname(abspath(__file__))` + `sys.path.insert(0, ENGINE_ROOT)` for sibling imports, then `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` for host paths. The two are deliberately distinct (engine location vs host checkout root) so the engine can one day be an installed plugin (`scripts/qrspi_paths.py:1-32`).
- **Single-JSON-envelope-on-stdout contract**: every `scripts/qrspi_*.py` CLI prints exactly one `json.dump(env, sys.stdout, indent=2); print()` and exits 0/1; diagnostics go to stderr. The JS orchestrator parses the worker's echo of that envelope with `extractJsonObject` + `JSON.parse` + defensive field validation, treating a garbled echo as a clean `ok:false`.
- **Pure-core / thin-imperative-shell split**: pure functions (banner `# --- pure helpers (unit-tested) ---`) take args + return values; subprocess/git/gh seams (banner `# --- ... (not unit-tested) ---`) are excluded from unit tests. The resolver `resolve()` is the strongest example — fully pure, takes `ci_revise_cap` as data (the precedent for threading a clock/elapsed-time in as data, not reading it).
- **Configuration is flat-top-level-key only**: no dot-path reader exists; numeric keys are read via `read_config().get(key)` + a `coerce_*` defensive coercer (`coerce_cap` rejects bool/float/str/non-positive → default 3). The JS `parseConfigEnvelope` additionally rejects non-string values — a constraint for any new config surfaced through the CLI envelope.
- **Worker prompts are maximally constrained**: "Run EXACTLY this one command verbatim — no path edits, no exploration, no alternatives, HARD STOP on ok:false." The weak local worker model is assumed to mangle paths (the `qrspi` token, `engineCmd` vs `engineCmdFor`), so determinism is pushed into self-locating scripts and the JS only orchestrates.
- **Durable counters live in git trailers**: `CI-Revise-Attempt: N` on the head commit is the GitHub-observable, resume-safe counter; the parse regex is duplicated verbatim between writer (`qrspi_ci_revise_bump.py`) and reader (`qrspi_pr_state.py`) as a shared serialization contract.

## Inconsistencies

- **`committedDate` is needed by the ticket's premise but never fetched today.** The GraphQL `PR_QUERY` (`scripts/qrspi_pr_state.py:26-69`) selects the head commit `message` + `statusCheckRollup` but NOT `committedDate`/`authoredDate`/`pushedDate`, and the resolver has no clock at all. Any elapsed-time backoff requires NEW data plumbing (gather fetch + pass-through into the pure resolver). This is a genuine gap, not an existing mechanism to extend.
- **Two divergent storage locations for "per-ticket durable output".** The critic-metrics ledger lives INSIDE the worktree (`<root>/.worktrees/<id>/.qrspi/<id>/...`, `qrspi_metrics_append.py:60-64`) and is therefore DESTROYED by `qrspi_cleanup.py`. The questions presuppose the observability file lives in the MAIN checkout (`<root>/.qrspi/observability/<id>.events.jsonl`) to survive cleanup. These are opposite conventions; the new feature deliberately departs from the metrics-ledger precedent on path (and likely on failure posture: metrics is fail-CLOSED, observability would be fail-OPEN/best-effort).
- **Two test styles coexist** under the same runner: raw-`assert` + `CASES` table (`qrspi_resolve_state_test.py`) vs `unittest.TestCase` (`qrspi_metrics_append_test.py`). Both pass `run_tests.py`, but they are not uniform — a new test author must pick one; the resolver-adjacent tests favor the raw-assert table style.
- **Stale doc reference noted in code**: `qrspi_critic_metrics.py:36-38` flags that `design.md:76` is stale (lists only `converged/cap_reached` terminal actions; the faithful four-value set is in the code). Not directly load-bearing for RUS-86 but illustrates the repo's habit of annotating doc/code drift inline rather than fixing the doc.
