# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Q1: How does `qrspi-batch.js` currently emit per-phase transitions (phase start/end, success, failure, retry) — where in the batch loop does each phase begin and end, and what data is available at those points to populate an event's `event_type`, `phase`, `actor`, and `message`?

**Answer:** There is NO structured per-phase event emission today. Transitions are surfaced only via two harness-injected globals: `phase('<Label>')` (declares the active UI phase) and `log('<freeform string>')` (human-readable progress). Neither is defined in the file — both are injected by the Workflow runner (the file is harness-coupled; see the `meta` block at lines 1-15 and the absence of any `const log`/`const phase` definition). The per-ticket loop is the natural emission site: each iteration runs `resolveTicket` → `ensureRestacked` → a `switch (a)` on `r.decision.action` dispatching to `doDesign/doPlan/doImplementation/doSubmit/doReset/doRevise/doLand/skip`. At dispatch time the following data is in scope: `t.id`, `t.status`, `t.title`, `r.decision.action`, `r.decision.phase`, `r.decision.nextPhase`, `r.decision.reason`, `r.decision.ciFailing/ciGaveUp/changeRequested`, and the returned `res.action/res.newStatus/res.ciGaveUp/res.ciReviseBumpFailed`.

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
  ...
}
results.push(res)
```

— `.claude/workflows/qrspi-batch.js:2690-2712`

Phase boundaries today are the `phase('<Label>')` calls only: `phase('Resolve')` (1382), `phase('Design')` (1529), `phase('Plan')` (1650), `phase('Implementation')` (1749), `phase('Finalize')` (1607,1674,1887,1906,1920,1968,2312), `phase('Reconcile')` (2427), `phase('Query')` (2467), `phase('Sync')` (2649), `phase('Restack')` (2682).

**Dependencies:** `log`/`phase`/`agent` are injected by the Workflow harness; the per-ticket `switch` consumes the resolver decision (`scripts/qrspi_resolve_state.py` shape). Each `do*` returns a result object pushed into `results[]`.
**Implicit contracts:** Result objects use `{ ticketId, action, summary, newStatus?, ciGaveUp?, ciReviseBumpFailed?, reconcileRetry? }` (see `skip()` at 650-658 and the trailing `log` at 2719). The UI-phase label vocabulary (`Resolve/Design/Plan/Implementation/Finalize/Reconcile/Query/Sync/Restack`) is distinct from the resolver's machine phase vocabulary (`design/plan/implementation`) — see Q11.

## Q2: Where is the per-invocation `runId` generated and how is it threaded through the batch loop, so an event emitter can attach it to `context.run_id`?

**Answer:** `runId` is computed ONCE at module top (the imperative shell) and is a free `const` in scope for the whole script, including the per-ticket loop. Precedence: `process.env.QRSPI_RUN_ID` → `crypto.randomUUID()` → a `crypto.getRandomValues`-derived `run-<hex>` → the constant `'run-fallback'`. Workflow scripts forbid `Date.now()`/`Math.random()` (they break resume), so no timestamp-based id is used. It is currently threaded into exactly ONE consumer: the critic-metrics appender, spliced into the worker command as `--run-id '${runId}'`.

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

— `.claude/workflows/qrspi-batch.js:133-141`

Existing consumption — spliced into the critic-metrics shell-out:

```
... python3 ${engineCmd('scripts/qrspi_metrics_append.py')} --ticket ${id} --run-id '${runId}' --record "$(cat ...)" ...
```

— `.claude/workflows/qrspi-batch.js:995`

**Dependencies:** `crypto` global; optional `process.env`. The metrics appender (`qrspi_metrics_append.py`) requires `--run-id` and stamps it onto every ledger line via `wrap_envelope(...)` (`scripts/qrspi_metrics_append.py:67-79,111-113`).
**Implicit contracts:** "runId always present, always a string" (the appender requires it; the constant `'run-fallback'` guarantees non-empty). Any new emitter can read this same module-level `runId` directly — no threading needed within the script.

## Q3: How is the active phase's `span_id` held during a phase so that nested critic-run, retry, and command shell-out events can receive it as `parent_span_id` — what local/loop state currently exists that the orchestrator could thread through?

**Answer:** There is NO span/span_id concept today — grep for `span` returns nothing in the workflow or scripts. The only per-step identity that exists is the `label` string passed to every `agent(prompt, { label, phase, agentType, schema })` call, which is unique per step (e.g. `critic:${id}:${name}:${lens}#${round + 1}`, `revise:${t.id}`, `finalize-design:${t.id}`). Loop/local state that an orchestrator could thread as a parent: `t.id` (per ticket), `r.decision.phase` (the resolver's machine phase), the `do*` function scope, and the round counters inside `runCriticPanelLoop` (`round`, `maxRounds`) and `bumpCiReviseTrailers` (per-branch loop). Nesting is structural (function call depth), not tracked by any id.

**Evidence:**

```
const agentOpts = { label: `critic:${id}:${name}:${lens}#${round + 1}`, phase: 'Critic', agentType, schema: CRITIC_VERDICT_SCHEMA }
```

— `.claude/workflows/qrspi-batch.js:794`

```
async function runPhase(name, agentType, prompt, existing, id, phaseLabel, criticConfig) {
  ...
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
```

— `.claude/workflows/qrspi-batch.js:1305-1310`

**Dependencies:** The `agent()` global; the `label`/`phase` option fields.
**Implicit contracts:** `label` is a free-form unique-per-step string; nothing currently consumes it as a correlation id. A new emitter would need to MINT span ids (the codebase provides none) — likely derived the same way as `runId` (crypto, never `Date.now()`/`Math.random()`).

## Q4: What is the existing convention for shared importable Python helper modules invoked by both the scripts and the orchestrator (e.g. `qrspi_config.py`, `qrspi_resolve.py`), including self-location of the repo root and stdlib-only constraints, that the new shared logger module must follow?

**Answer:** Established convention (stdlib-only, self-locating, JSON-envelope-on-stdout). Two distinct self-location idioms exist:

1. **`__file__` two-levels-up** for pure config reads that key off the INVOKED checkout: `REPO_ROOT = Path(__file__).resolve().parents[1]` (`qrspi_config.py:29`).
2. **`qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)`** for anything that must land in the MAIN checkout even when invoked from a worktree (git-common-dir first). Used by `qrspi_metrics_append.py`, `qrspi_cleanup.py`, `qrspi_ci_revise_bump.py`. The pattern: `ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ENGINE_ROOT); import qrspi_paths`. **This is the critical choice for the event log** (see Q7).

Every helper: stdlib-only, `argparse` CLI, prints a single JSON envelope to stdout, has a `_test.py` sibling, and separates PURE helpers (unit-tested) from subprocess/IO mechanics.

**Evidence:**

```
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)
import qrspi_paths  # noqa: E402
...
REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)
```

— `scripts/qrspi_metrics_append.py:52-55,131`; identical idiom at `scripts/qrspi_cleanup.py:45-58`, `scripts/qrspi_ci_revise_bump.py:54-59`

`resolve_repo_root` precedence: `--repo-root` (validated) → git-common-dir (validated) → `__file__` fallback (`scripts/qrspi_paths.py:19,111-117`).

**Dependencies:** `scripts/qrspi_paths.py` (the shared root resolver). No third-party imports anywhere in `scripts/`.
**Implicit contracts:** `validate=False` keeps `gh` off the import path. The qrspi-laden canonical path is computed BY THE SCRIPT, never typed by a model. Output is a single JSON envelope `{ ok, ..., error? }`, exit 0/1.

## Q5: How does the orchestrator currently shell out to Python scripts and consume their output, given the constraint that stdout carries JSON envelopes the orchestrator parses and CLI logs must go only to stderr/`cli.log`?

**Answer:** The orchestrator NEVER runs Python directly (the JS sandbox cannot exec). It spawns a thin worker agent whose prompt contains the EXACT verbatim command, and the worker returns the script's JSON stdout. Two consumption modes: (a) StructuredOutput via a `schema` (e.g. `PERSIST_SCHEMA`, `CI_REVISE_BUMP_SCHEMA`) returned as a parsed object; (b) no-schema plain-text return then `JSON.parse` on the JS side (e.g. `parseResolveEnvelope`, `parseConfigEnvelope` — each guards `try { JSON.parse } catch`). Commands are built with `engineCmd(rel)` (runner cwd) or `engineCmdFor(r, rel)` (worker cwd = worktree). Scripts print ONLY their JSON envelope to stdout; there is no `cli.log` file and no stderr-routing convention in the repo today (grep for `cli.log`/`console.error`/`process.stderr` returns nothing) — the "stdout carries JSON, logs to stderr" discipline the ticket assumes is NOT yet implemented.

**Evidence:**

```
async function persistArtifact(id, name, phaseLabel) {
  return await agent(
    `You are the PERSIST worker ... Run EXACTLY this one command verbatim ...
  python3 ${engineCmd('scripts/qrspi_persist.py')} --ticket ${id} --artifact ${name}
... Parse that JSON and return it verbatim. ...`,
    { label: `persist:${id}:${name}`, phase: phaseLabel, schema: PERSIST_SCHEMA }
  )
}
```

— `.claude/workflows/qrspi-batch.js:676-689`

Plain-text + `JSON.parse` mode: `parseConfigEnvelope` `try { env = JSON.parse(raw) } catch (e) { return { ok: false, error: ... } }` (`.claude/workflows/qrspi-batch.js:385`); `parseResolveEnvelope` at 263.

**Dependencies:** `engineCmd`/`engineCmdFor` (76,105); the `agent()` global; per-call `schema` constants.
**Implicit contracts:** A script that writes ANYTHING non-JSON to stdout breaks the `JSON.parse`. A new logger must therefore write its log to a FILE (or stderr), never stdout, when invoked in this worker-parse path. The worker is instructed "no path edits, no exploration, no alternatives, HARD STOP on ok:false."

## Q6: How does `scripts/qrspi_config.py` read configuration keys, and does it support the nested `observability.*` block and top-level `ciReviseBackoffBase`/`ciReviseBackoffCap` keys this ticket requires, or only single top-level keys?

**Answer:** `qrspi_config.py` reads ONE top-level key only via `--key <name>` and returns its value through the pure selector `select_value(config, key, default)` which does `config.get(key)` (no dot-path, no nesting). It has a per-key DEFAULTS map (`{"linearProject": "QRSPI"}`); unknown keys default to `""`. It returns truthy-or-default, so a value of `0`/`false`/`""` collapses to the default. It does NOT support nested blocks like `observability.*`, and the new top-level keys `ciReviseBackoffBase`/`ciReviseBackoffCap` do NOT exist anywhere in the repo (grep for `ciReviseBackoff`/`backoff` finds only `grade.py`'s unrelated judge retry). `.qrspi/config.example.json` has NO `observability` block and NO backoff keys; it carries `ciReviseCap` (flat, default 3) and a NESTED `critics.*` block (read by a SEPARATE resolver, `qrspi_critics_config.py`, not `qrspi_config.py`).

**Evidence:**

```
DEFAULTS = {"linearProject": "QRSPI"}

def select_value(config: dict, key: str, default: str) -> str:
    value = config.get(key)
    return value if value else default
```

— `scripts/qrspi_config.py:33,36-42`

**Dependencies:** Reads `<repo_root>/.qrspi/config.json` best-effort (returns `{}` on OSError/ValueError; `read_config` 45-56). Note: `.qrspi/config.json` does not exist in the worktree (only `.example.json`), so the harness runs on defaults.
**Implicit contracts:** Single-key-only, string-valued, truthy-or-default. A nested `observability.*` read needs a NEW reader (mirroring `qrspi_critics_config.py`, which reads the nested `critics` block) or a config.py extension. The JS side `parseConfigEnvelope` also rejects non-string values in some paths (per project MEMORY: "JS parseConfigEnvelope rejects non-string values").

## Q7: How and where does `qrspi_cleanup.py` tear down worktrees, and what currently lives under the worktree's `.qrspi/<id>/` versus the main checkout, to confirm that writing the event log to the main checkout survives teardown?

**Answer:** `qrspi_cleanup.py` destroys a fully-merged ticket's worktree via `git worktree remove --force <wt_path>` where `wt_path = REPO_ROOT/.worktrees/<id>` (`_remove_worktree` 168-180; `worktree_path` imported from `qrspi_restack`). It ALSO deletes local `<id>/*` branches and prunes merged remote refs. Per-ticket artifacts (including the critic-metrics ledger) currently live UNDER the worktree at `<root>/.worktrees/<id>/.qrspi/<id>/` — see `qrspi_metrics_append.ledger_path` (`scripts/qrspi_metrics_append.py:60-64`) and `qrspi_persist.py`'s destination. **Therefore anything under `.worktrees/<id>/.qrspi/<id>/` is DESTROYED at teardown.** To survive teardown, the event log must be written to the MAIN checkout (`<root>/.qrspi/observability/...`), NOT the worktree's `.qrspi/<id>/`. `resolve_repo_root` (git-common-dir first) yields that main-checkout root even when invoked from a worktree — this is the exact seam to use.

**Evidence:**

```
def _remove_worktree(wt_path, dry_run):
    if not os.path.isdir(wt_path):
        return False
    ...
    rc, out, err = _run(["git", "worktree", "remove", "--force", wt_path], cwd=REPO_ROOT)
```

— `scripts/qrspi_cleanup.py:168-180`

```
def ledger_path(repo_root, ticket):
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket,
                        "critic-metrics.jsonl")
```

— `scripts/qrspi_metrics_append.py:60-64` (an example of a per-ticket artifact that DOES live in the worktree, hence dies at cleanup)

**Dependencies:** `qrspi_restack.worktree_path`, `qrspi_pr_state` (merge state), `qrspi_paths`. Cleanup is opt-in (the Reconcile pass) and gated behind a `destroy` classification (fully merged + clean).
**Implicit contracts:** `.worktrees/` is gitignored; the main `.qrspi/<id>/` is committed per phase. The main-checkout `.qrspi/` survives worktree teardown. Cleanup is idempotent (missing worktree = clean no-op).

## Q8: How does the resolver currently read and write the `CI-Revise-Attempt` head-commit trailer and the `committedDate` of the frontier head commit, since the new backoff policy derives `retry_attempt` from that trailer and measures elapsed time from that date?

**Answer:** **The trailer:** read (not written) by the resolver. The gather (`qrspi_pr_state.py`) parses the trailer from the head-commit message with `_CI_REVISE_ATTEMPT_RE = ^CI-Revise-Attempt:\s*(\d+)\s*$` (MULTILINE, last-occurrence-wins) in `ci_revise_attempt(message)`, then exposes it on each phase as `ciReviseAttempt`, BUT forced to 0 whenever `ciState != "red"` (the read-side reset). The pure resolver reads that field via `ci_revise_attempt_of(phases, name)` (max across slices for implementation). The trailer is WRITTEN by `qrspi_ci_revise_bump.py` (+1 on the CI-failure path) and reset to 0 by the CI-trailer-reset worker / `doRevise`. **`committedDate`: DOES NOT EXIST.** The GraphQL query selects `commits(last:1){ commit { message statusCheckRollup{...} } }` — NO `committedDate`/`authoredDate` field — and `build_state` exposes `mergedAt` but NOT any head-commit timestamp. The backoff policy's "elapsed time from committedDate" has NO existing data source; the GraphQL query and `build_state` output would need a NEW field added.

**Evidence:**

```
commits(last:1) {
  nodes {
    commit {
      message
      statusCheckRollup { state contexts(first:100){ ... } }
    }
  }
}
```

— `scripts/qrspi_pr_state.py:48-64` (note: no `committedDate`)

```
if ci_state == "red":
    attempt = ci_revise_attempt(_head_commit(node).get("message"))
else:
    attempt = 0
return { ..., "ciState": ci_state, "ciFailingChecks": failing, "ciReviseAttempt": attempt }
```

— `scripts/qrspi_pr_state.py:303-321`

Resolver read seam: `ci_revise_attempt_of(phases, name)` (`scripts/qrspi_resolve_state.py:129-138`).

**Dependencies:** Gather (`qrspi_pr_state.py`) → resolver (`qrspi_resolve_state.py`); writer = `qrspi_ci_revise_bump.py`. The trailer is the shared serialization contract between writer and reader (identical regex in both files).
**Implicit contracts:** Trailer parse: absent⇒0, last-occurrence wins. The effective `ciReviseAttempt` is already not-red→0 normalized at gather time, so the resolver reads it directly. **A backoff needing `committedDate` must first add `committedDate` to the GraphQL selection AND to `build_state`'s output dict (additive, mirroring how `mergedAt` is carried).**

## Q9: Where is the consecutive-red `ciReviseCap` cap counter evaluated in the resolver's decision precedence (after the unified-feedback handler, before the active-phase block), so the new backoff gate can be placed correctly relative to it?

**Answer:** The CI cap is evaluated in step **2c (CI-gated revise/wait)** of `resolve()`, slotted AFTER the unified-feedback handler (2b) and BEFORE the active-phase block (step 3). It operates ONLY on the frontier (`frontier = max(existing, key=_order)`). Flow: `fci = ci_state(phases, frontier)`; if `fci == "red"` then `attempt = ci_revise_attempt_of(phases, frontier)` and `if attempt < ci_revise_cap` → `revise (ciFailing=True)`, else → `wait (ciFailing=True, ciGaveUp=True)`; if `fci == "pending"` → `wait`; green/none falls through. `ci_revise_cap` is a parameter to `resolve(state, ci_revise_cap=3)` (passed in by the caller, default 3) — the resolver does NO disk read. This is the exact slot a backoff gate would sit in (between 2b and step 3, governing the red frontier).

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

**Dependencies:** `ci_state` (110-126), `ci_revise_attempt_of` (129-138), `phase_changes_requested`, `phase_comment_targets`. Cap value threaded from `qrspi_resolve.py` (config `ciReviseCap`).
**Implicit contracts:** Only the FRONTIER's CI gates; a non-frontier red PR takes no CI action (its upstream already merged; non-frontier CHANGES_REQUESTED reset at step 2). "cap-then-wait": at/above cap → `wait` with `ciGaveUp=True`. The decision dict already carries `ciFailing`/`ciGaveUp` fields (185-198) — a `backoffWaiting`-style field would be additive there.

## Q10: How is the resolver's clock/time access currently structured, and is there an existing seam for injecting a clock, since the backoff policy must be unit-tested in the resolver with an injected clock?

**Answer:** The resolver `qrspi_resolve_state.py` has NO clock/time access at all — it imports only `argparse`, `json`, `sys` (lines 57-59). `resolve(state, ci_revise_cap=3)` is a PURE function with NO `datetime`/`time` import and no `now()` call. There is NO existing clock-injection seam. The established pattern for time-dependent logic with a test seam is elsewhere: `qrspi_metrics_append.py` calls `datetime.now(timezone.utc).isoformat()` directly in `main()` (not injected — `scripts/qrspi_metrics_append.py:133`), and `grade.py` uses `time.sleep` for backoff. The cleanest fit for the ticket's "injected clock" requirement is to add a default-arg seam to `resolve()` (e.g. `resolve(state, ci_revise_cap=3, now=None)`), since the function is already parameterized that way for `ci_revise_cap` (passed in, defaulted, keeping the function pure and disk-free — Q9). The `committedDate` it would compare against does not yet exist (Q8).

**Evidence:**

```
import argparse
import json
import sys
```

— `scripts/qrspi_resolve_state.py:57-59` (the COMPLETE import set — no time/datetime)

```
def resolve(state, ci_revise_cap=3):
    """... `ci_revise_cap` is passed IN by the caller ... so this function stays pure
    and does no disk read ..."""
```

— `scripts/qrspi_resolve_state.py:173-181` (the existing default-arg injection pattern to mirror for a clock)

**Dependencies:** None for time. The unit-test harness `qrspi_resolve_state_test.py` builds `state` dicts and calls `resolve(state, ...)` directly with assert-based tests.
**Implicit contracts:** `resolve` must stay PURE (no I/O), so a clock MUST be injected as a parameter (default-arg), not read from the wall clock inside the function — otherwise the existing purity/testability contract breaks. The test sibling already passes scalars in; an injected `now` (e.g. epoch seconds or a `datetime`) fits the same style.

## Q11: What is the established machine vocabulary for `phase` values in the resolver (`design`/`plan`/`implementation` vs `implement`) and for `actor`/`status`, so the `events.schema.json` enums match the tested resolver exactly rather than diverging?

**Answer:** **Phase:** the resolver's machine vocabulary is exactly `["design", "plan", "implementation"]` — `PHASES = ["design", "plan", "implementation"]` (`scripts/qrspi_resolve_state.py:61`). It is `implementation`, NOT `implement`. `decision.phase`/`nextPhase`/`resetToPhase` all draw from this set; note `advance(implementation→implementation)` is used for the incomplete-stack resume (353). The critic-metrics phase label is `design` (passed `--phase design`). **Note a competing vocabulary:** the batch UI `phase('<Label>')` uses Title-Case labels (`Design`/`Plan`/`Implementation`/`Finalize`/`Resolve`/...) — these are DISPLAY labels, not the machine phase. The `events.schema.json` `phase` enum should match the resolver's lowercase set. **Actor:** NO `actor` field exists anywhere — grep for `"actor"` returns nothing. There is no established actor vocabulary; it would be net-new (candidates from existing concepts: orchestrator, resolver, the worker agentTypes like `qrspi-design`/`qrspi-implement`). **Status:** the resolver uses `linearStatus == "Selected"` as the entry gate (`scripts/qrspi_resolve_state.py:211`); Linear reporting statuses are `Selected/Design Review/Plan Review/Code Review/Done` (CLAUDE.md). The critic-step terminal vocabulary is `converged/cap_reached/exhausted/aborted` (`qrspi_critic_metrics.py:50-51`). The decision ACTIONS vocabulary is `entry_blocked/run_design/submit/wait/revise/advance/land/reset` (`qrspi_resolve_state.py:68-77`).

**Evidence:**

```
PHASES = ["design", "plan", "implementation"]
```

— `scripts/qrspi_resolve_state.py:61`

```
ACTIONS = ("entry_blocked","run_design","submit","wait","revise","advance","land","reset")
```

— `scripts/qrspi_resolve_state.py:68-77`

```
VALID_TERMINAL_ACTIONS = frozenset({"converged", "cap_reached", "exhausted", "aborted"})
```

— `scripts/qrspi_critic_metrics.py:50-51`

**Dependencies:** `PHASES` is the single source of truth for phase ordering (`_order`, `_pr_*` helpers). The batch maps `nextPhase` strings (`'plan'`/`'implementation'`) in its dispatch switch (`qrspi-batch.js:2696-2697`).
**Implicit contracts:** Phase is lowercase `implementation` (NOT `implement`), though the worker AGENT TYPE is `qrspi-implement` (singular) — a known naming split. Any schema enum must use the resolver's lowercase machine set, not the Title-Case UI labels nor the agentType spellings.

## Q12: How does the existing metrics ledger implement its fail-CLOSED posture, so the new fail-OPEN emitter and CLI logger can be the deliberate opposite (write/flush/fsync failures logged-and-swallowed, pipeline continues)?

**Answer:** The critic-metrics ledger (`qrspi_metrics_append.py`) is the canonical fail-CLOSED sink. Its posture: (1) malformed `--record` JSON → exit 1, write nothing; (2) `append_line` writes the JSON line, then VERIFIES the file is non-empty (`os.path.getsize`), returning an error if 0 bytes; (3) `main()` returns `0 if error is None else 1`, so any write failure exits NON-ZERO. On the JS side, the appender is chained with `&&` into the critic-metrics shell-out so a non-zero appender exit FAILS the whole chain — the worker surfaces null and the caller treats the step as failed (it does NOT silently skip). To be the deliberate OPPOSITE (fail-OPEN), the new emitter/logger must: catch all OSError/IOError around open/write/flush/fsync, log-and-swallow (never raise, never non-zero exit on a write failure), and the orchestrator must NOT `&&`-chain it into a gating command nor treat its failure as a phase failure.

**Evidence:**

```
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
    ...
    return lines, size, None
```

— `scripts/qrspi_metrics_append.py:82-99`

```
return 0 if error is None else 1
```

— `scripts/qrspi_metrics_append.py:149` (non-zero on any write error = fail-CLOSED)

JS gating chain (`&&` makes a failed append fail the step): `.claude/workflows/qrspi-batch.js:995`.

**Dependencies:** `qrspi_paths.resolve_repo_root`; `datetime.now(timezone.utc)` for the timestamp.
**Implicit contracts:** Fail-closed = "a bad write is never silent; exit non-zero; the chained caller stops." The fail-OPEN inversion = "wrap every fs op in try/except, swallow, return ok:true (or just log), and never `&&`-gate the pipeline on it." Note the codebase's house style elsewhere ALSO has a fail-OPEN precedent: `parseCriticPhasesEnvelope` falls back to defaults on a garbled config and "NEVER gates the run" (`qrspi-batch.js:397-411`) — a model for swallow-and-continue.

## Q13: What is the existing stdlib-only unit-test pattern (`scripts/*_test.py`, the `run_tests.py` aggregating runner) that tests for the event emitter, log rotator, retention cleaner, and resolver backoff must conform to?

**Answer:** Pattern: each `scripts/<name>_test.py` is a standalone, stdlib-only, assert-based (no pytest) script that exits 0 on success / 1 on first failure, importing the module-under-test directly (e.g. `from qrspi_resolve_state import resolve`). The aggregating runner `run_tests.py` discovers every `scripts/*_test.py` via `discover_tests` and runs each as its own subprocess (`run_one`/`run_suite`) with a 180s per-file timeout, printing PASS/FAIL and exiting non-zero if any fail. It is the CI gate (`.github/workflows/tests.yml`). Test files use small builder helpers for fixtures (e.g. `_phase`, `_impl`, `_slice` in `qrspi_resolve_state_test.py`). Pure functions are tested directly; subprocess/IO mechanics are tested against temp dirs (the metrics appender / cleanup pattern) or left to manual e2e.

**Evidence:**

```
def discover_tests(scripts_dir=SCRIPT_DIR, pattern=None):
    names = sorted(n for n in os.listdir(scripts_dir) if n.endswith("_test.py"))
    ...
def run_one(path, python=None, timeout=DEFAULT_TIMEOUT):
    proc = subprocess.run([python, path], capture_output=True, text=True, timeout=timeout)
    ok = proc.returncode == 0
```

— `scripts/run_tests.py:36-67`

Test sibling shape (assert-based, direct import, fixture builders):

```
from qrspi_resolve_state import resolve

def _phase(branch=True, pr=True, decision="REVIEW_REQUIRED", threads=0, ...):
    return {"branchExists": branch, "prExists": pr, ...}
```

— `scripts/qrspi_resolve_state_test.py:11-18`

**Dependencies:** `run_tests.py` self-locates `SCRIPT_DIR` from `__file__`; no third-party. New tests auto-discovered by the `*_test.py` suffix.
**Implicit contracts:** Filename MUST end `_test.py` to be discovered. Exit 0/non-zero is the contract (the runner keys off returncode). Stdlib-only; assert-based; `__main__`-guarded. A test that hangs >180s fails. New backoff/emitter/rotator/retention tests must each be a `scripts/*_test.py` and will be picked up automatically.

## Q14: Is there any pre-existing logging, event emission, or `.qrspi/observability/` writing in the codebase today (the ticket states the pipeline has no backoff policy and no structured log), so the new logger is built net-new rather than duplicating an existing facility?

**Answer:** Built NET-NEW. There is NO `.qrspi/observability/` writer, NO structured event log, and NO Python `logging` usage. Grep for `observability` finds only doc COMMENTS (calling `mergedByPr`/`ciReviseAttempt` "additive observability" — `qrspi_pr_state.py:345,627`; `qrspi-batch.js:2010`), never a writer. Grep for `getLogger`/`logging.` in `scripts/` and `.claude/` returns nothing. The CLOSEST existing facilities: (1) the critic-metrics JSONL ledger at `.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl` (per-ticket, in the WORKTREE, dies at cleanup — Q7); (2) the harness-injected `log()` free-form string output in the workflow; (3) the `results[]` array the batch returns. No `events.schema.json` exists (find returns nothing). The backoff policy is also genuinely absent (the only "backoff" in the repo is `grade.py`'s unrelated LLM-judge retry).

**Evidence:**

```
$ grep -rn "observability\|getLogger\|logging\." scripts/ .claude/
scripts/qrspi_pr_state.py:345:    mergedByPr is purely additive observability ...
scripts/qrspi_pr_state.py:627:    # is additive observability — no consumer ...
.claude/workflows/qrspi-batch.js:2010:    // ... so this is durability/observability
$ find . -name "*.schema.json"   # (no output)
```

— repo-wide grep / find results

**Dependencies:** None — net-new. The only adjacent durable sink is the critic-metrics ledger (`qrspi_metrics_append.py`), a model for the JSONL-append style but in the wrong (worktree) location for survival.
**Implicit contracts:** No facility to duplicate or extend; the logger is a clean new module. It should follow the shared-helper conventions (Q4): stdlib-only, self-locating via `qrspi_paths` (main checkout), JSONL-append style like the metrics ledger but written to the MAIN `.qrspi/observability/`.

## Q15: How is JSON validation handled elsewhere in the repo (stdlib-only, no third-party schema libs), to inform the hand-rolled validator that must load `event_type`/`status`/`phase` enums from `events.schema.json` as the single source of truth?

**Answer:** All JSON validation is hand-rolled with `json` + plain Python — NO `jsonschema`/third-party libs (none in `requirements.txt`; none imported). The enum-validation idiom: a module-level `frozenset`/`set` of valid values plus an explicit membership check raising `ValueError` (fail-closed). Canonical example: `qrspi_critic_metrics.py`'s `VALID_TERMINAL_ACTIONS = frozenset({...})` with `if terminalAction not in VALID_TERMINAL_ACTIONS: raise ValueError(...)`. Parsing is `json.loads` in a `try/except (ValueError, TypeError)` that exits non-zero on malformed input (`qrspi_metrics_append.py:117-129`). On the JS side, StructuredOutput `schema` objects (`{ type, required, properties }`) are passed to `agent()`, and `JSON.parse` is wrapped in `try/catch`. Today the enums are hard-coded constants IN each module — there is NO shared `events.schema.json` loaded as a single source of truth (none exists), so the ticket's "load enums from events.schema.json" is a NEW pattern; the closest precedent is reading a JSON file best-effort then validating in-Python (`qrspi_config.read_config` / `qrspi_critics_config.py`).

**Evidence:**

```
VALID_TERMINAL_ACTIONS = frozenset({"converged", "cap_reached", "exhausted", "aborted"})
...
if terminalAction not in VALID_TERMINAL_ACTIONS:
    raise ValueError("invalid terminalAction %r; must be one of %s ..." % (...))
```

— `scripts/qrspi_critic_metrics.py:50-51,76-80`

```
try:
    record = json.loads(args.record)
except (ValueError, TypeError) as exc:
    env = {"ok": False, "error": "invalid --record JSON: %s" % exc}
    json.dump(env, sys.stdout, indent=2); print(); return 1
```

— `scripts/qrspi_metrics_append.py:117-123`

**Dependencies:** stdlib `json` only. `read_config` (`qrspi_config.py:45-56`) is the best-effort JSON-file loader pattern to mirror for loading `events.schema.json`.
**Implicit contracts:** Validation is membership-against-a-frozenset + `ValueError` (fail-closed) OR best-effort-default (fail-open, e.g. `parseCriticPhasesEnvelope`). To make `events.schema.json` the single source of truth, the validator must LOAD that file and derive its enums from it at runtime (new) rather than hard-coding a `frozenset` — but the in-Python membership-check + raise idiom stays.

---

## Discovered Patterns

- **Self-location is mandatory and has two flavors.** Worktree-surviving artifacts MUST use `qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` (git-common-dir first → MAIN checkout); pure config reads keyed to the invoked checkout use `Path(__file__).resolve().parents[1]`. The event log must use the FORMER to land in the main checkout and survive cleanup (Q7).
- **The qrspi path token is never typed by a model.** Every canonical path is computed BY a script; workers run verbatim commands. This is a deliberate defense against the weak local worker model mangling `qrspi`→`qrpii` (Fix A / persist). A new logger should own its path the same way.
- **Pure core + IO shell + `_test.py` sibling** is the universal script shape. Pure functions (selectors, reducers, classifiers) are unit-tested; subprocess/network mechanics are not (manual e2e). New emitter/rotator/retention/backoff logic should isolate the pure decision (e.g. "should I back off given attempt N, elapsed T") for unit testing.
- **`resolve()` injects scalars as default-args to stay pure.** `ci_revise_cap=3` is passed in, not read. A clock for backoff should follow this (`now=...` default-arg), never read the wall clock inside the pure function (Q10).
- **Two fault postures coexist deliberately.** Fail-CLOSED for durable correctness gates (metrics append, persist, citation node-check — non-zero exit, `&&`-chained). Fail-OPEN for non-gating enrichment (`parseCriticPhasesEnvelope` falls back to defaults and "NEVER gates the run"). The ticket's emitter/logger belongs in the fail-OPEN camp (Q12).
- **Enums are hard-coded frozensets per module today**; there is no shared schema file. Centralizing enums in `events.schema.json` is a genuinely new convention (Q15).
- **`log`/`phase`/`agent`/`crypto` are harness-injected globals**; `qrspi-batch.js` is not unit-testable in isolation (no imports, top-level `return`). JS-side observability wiring is verified by manual e2e, not unit tests (per CLAUDE.md / project MEMORY).

## Inconsistencies

- **`committedDate` does not exist but the ticket's backoff requires it (Q8).** The GraphQL query (`qrspi_pr_state.py:48-64`) selects no head-commit timestamp, and `build_state` exposes none. "Elapsed time from committedDate" has no current data source — it must be added to BOTH the GraphQL selection and `build_state` output (additive, like `mergedAt`).
- **Phase-vocabulary split: `implementation` (resolver machine value) vs `qrspi-implement` (agentType) vs `Implementation` (UI label).** `PHASES = [..., "implementation"]` (singular machine value is `implementation`, NOT `implement`), but the worker agentType is `qrspi-implement` (singular) and the UI `phase()` label is Title-Case `Implementation`. The `events.schema.json` `phase` enum must follow the resolver's lowercase machine set (Q11).
- **Config keys the ticket assumes are absent.** `observability.*` (nested) and `ciReviseBackoffBase`/`ciReviseBackoffCap` (top-level) do NOT exist in `.qrspi/config.example.json` or any reader. `qrspi_config.py` reads single top-level keys only (no nesting). A nested-block reader (mirroring `qrspi_critics_config.py`) is required (Q6).
- **No `cli.log` / stderr-routing discipline exists** despite the ticket's framing ("CLI logs must go only to stderr/cli.log"). Today scripts print ONLY their JSON envelope to stdout; there is no stderr logging convention. The constraint the ticket assumes is itself part of the net-new work — and is load-bearing because the worker-parse path `JSON.parse`s stdout, so any log line on stdout would break parsing (Q5).
- **Doc staleness already flagged in-repo:** `design.md:76` lists only `converged/cap_reached` for the terminal-action enum while the code has four values — `qrspi_critic_metrics.py:36-38` notes this. A pattern of code/comment drift to watch when matching schema enums to the tested resolver (Q11).
- **The metrics ledger writes to the WORKTREE `.qrspi/<id>/` and therefore dies at cleanup** (`qrspi_metrics_append.ledger_path`), while phase artifacts under the MAIN `.qrspi/<id>/` are committed and survive. The new observability log must NOT replicate the metrics ledger's worktree location if it is meant to outlive teardown (Q7).
