# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## Q1: How does an `agent()` failure currently propagate out of `runPhase` and the critic loops — what value/exception does a failed `agent()` call yield, and where is that failure first observed and acted on?

**Answer:** `agent()` is a harness-INJECTED global (not defined in `qrspi-batch.js`; see Q3/Discovered Patterns). On failure or skip it returns `null` — the codebase never observes an exception/throw from `agent()`; the universal failure signal is a `=== null` (or falsy) check on its return value. There is no error-string surfaced to the caller (see Q2). The failure is first observed at the call site that owns the `agent()` await, then converted into a control-flow signal:

- In `runPhase`, the producer result is checked: `if (res === null) { log(...); return false }` — a `false` return.
- In `runCriticLoop` / `runCriticPanelLoop`, a null critic/reviser/lens verdict returns `{ ok: false, residualFindings: [] }`, which `runPhase` turns into `return false`.
- In `runSliceCritic` / `runCoherenceCritic`, a null spawn returns a falsy/`ok:false` envelope that the slice loop turns into a `skip(...)` result.
- `runPhase`'s `false` propagates to `doDesign`/`doPlan` which return `failTicket(t)` — `{ ticketId, action:'failed', summary:'A phase agent failed; ticket left untouched (no fabrication).' }`. `doImplementation` returns `skip(t, r.decision, ...)` instead.

So the first observation is the `=== null` check at the immediate await; the first ACTED-ON point is the `return false` / `return skip(...)` that aborts the ticket. **A retry wrapper would need to intercept the `agent()` call itself (the await), because by the time `null` reaches `runPhase` the only signal left is "failed" with no error text.**

**Evidence:**

```js
async function runPhase(name, agentType, prompt, existing, id, phaseLabel, criticConfig) {
  if (existing && existing[name]) { log(`  ${id}: reusing existing ${name}.md`); return true }
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
  if (res === null) {
    log(`  ${id}: ${name} phase failed or was skipped — stopping this ticket`)
    return false
  }
```

— `.claude/workflows/qrspi-batch.js:1238-1247`

```js
function failTicket(t) {
  return { ticketId: t.id, action: 'failed', summary: 'A phase agent failed; ticket left untouched (no fabrication).' }
}
```

— `.claude/workflows/qrspi-batch.js:2269-2271`

```js
const verdict = await agent(`You are the qrspi-critic ...`, { label: `critic:${id}:${name}#${round + 1}`, ... })
if (verdict === null) {
  log(`  ${id}: ${name} critic round ${round + 1} failed/skipped — stopping this ticket`)
  return { ok: false, residualFindings: [] }
}
```

— `.claude/workflows/qrspi-batch.js:719-729`

**Dependencies:** `runPhase` ← `doDesign`/`doPlan`/`doImplementation` ← the main per-ticket dispatch `switch (a)` at `:2589-2599`. `failTicket`/`skip` results bubble to the run's results array.
**Implicit contracts:** Every `agent()` consumer treats `null` (or non-object/`ok:false`) as "stop this ticket, leave it untouched, fabricate nothing." There is exactly ONE return contract (`null` ⇒ failure) and NO exception path; a retry wrapper must preserve that `null`-on-exhaustion contract so all 12+ existing `=== null` checks keep working unchanged.

## Q2: What text/field carries the error signature for a failed agent job (e.g. `socket connection was closed unexpectedly`, `rate limit`, `monthly spend limit`), and is that string available to the caller in `qrspi-batch.js` at the point where a retry wrapper would inspect it?

**Answer:** NOT FOUND in the codebase as an exposed value. A grep across `.claude/workflows/qrspi-batch.js`, `scripts/`, and `docs/` for `socket connection`, `rate limit`, `429`, `529`, `ECONNRESET`, `fetch failed`, `terminated`, `monthly spend limit`, `spend limit`, `quota`, `usage limit` returns **zero** hits in code (only the questions.md/this-artifact references). The `agent()` failure contract surfaces only `null` to the caller (Q1) — no error object, no message string, no status code. The transient-error signatures listed in the questions are runtime/harness-level messages produced by the agent execution layer, which is an injected global outside this repo's source.

**Consequence for a retry wrapper:** at the current `agent()` seam there is NO error string available to inspect. To classify a failure signature, the wrapper must capture whatever the harness exposes when `agent()` fails (today: only a `null` return — the message is not threaded through). This is a genuine gap: the questions assume an inspectable signature, but the present return contract discards it. The design must specify HOW the signature is obtained (e.g. does the harness throw on the failure with a message before returning null? does it need a try/catch around the await?), because the JS source today only sees `null`.

**Evidence:**

```
$ grep -rni "socket connection|rate limit|529|ECONNRESET|fetch failed|spend limit|monthly spend" \
    .claude/workflows/qrspi-batch.js scripts/ docs/
# (no matches in code; only questions.md references the strings)
```

The only failure value reaching the caller:

```js
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
  if (res === null) { ... return false }
```

— `.claude/workflows/qrspi-batch.js:1243-1247`

**Dependencies:** `agent()` injected global (not in repo). No Python/JS error-signature plumbing exists.
**Implicit contracts:** The current contract is binary (`null` = fail). Any classifier needs an error STRING that the present seam does not provide; the wrapper must introduce the capture mechanism (likely a `try { await agent() } catch (e) { inspect e.message }`), since `agent()`'s exception/return behavior on a transient network error is not specified anywhere in-repo. **Flagged as an open dependency in Inconsistencies.**

## Q3: What is the exact signature and call convention of `agent()` at each of its call sites (`runPhase`, `runCriticLoop`, `runCriticPanelLoop`, `runSliceCritic`, coherence), so a wrapper can intercept all of them uniformly?

**Answer:** `agent()` is a uniform 2-arg injected global: `agent(promptString, optionsObject)`, returning a Promise that resolves to either the structured result (when `schema` is supplied) or a string/`null`. There are ~20 call sites; ALL follow the identical convention `await agent(<prompt>, { label, phase, agentType?, schema? })`:

- `label` (string, always present): the human-readable id, e.g. `` `${name}:${id}` ``, `` `critic:${id}:${name}#${round + 1}` `` (see Q5).
- `phase` (string, always present): the progress-display group, e.g. `'Design'`, `'Critic'`, `'Finalize'`, `'Reconcile'`.
- `agentType` (string, optional): the registered `.claude/agents/qrspi-*` type. Present for typed phase agents (`'qrspi-questions'`, `'qrspi-critic'`, `` `qrspi-design-critic-${lens}` ``); ABSENT for the generic worker agents (persist/resolve/config/reviser) that run shell commands.
- `schema` (object, optional): a `*_SCHEMA` StructuredOutput shape. When present `agent()` returns the parsed object (or `null`); when absent it returns the agent's final-message text (or `null`).

Because every call site is `await agent(prompt, opts)` with the same shape, a single wrapper `async function agentWithRetry(prompt, opts) { ... await agent(prompt, opts) ... }` can intercept all of them by replacing the `agent(` calls (or by defining the wrapper once and swapping call sites). The options object already carries `label`/`phase` for log lines (Q5/Q13).

**Evidence (representative call sites, identical convention):**

```js
const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })        // :1243 runPhase
const verdict = await agent(`You are the qrspi-critic ...`,
  { label: `critic:${id}:${name}#${round + 1}`, phase: 'Critic', agentType: 'qrspi-critic', schema: CRITIC_VERDICT_SCHEMA }) // :719-724 runCriticLoop
const verdict = await agent(`You are the ${lens} lens ...`,
  { label: `critic:${id}:${name}:${lens}#${round + 1}`, phase: 'Critic', agentType, schema: CRITIC_VERDICT_SCHEMA })          // :816-823 runCriticPanelLoop
const verdict = await agent(`You are the qrspi-coherence-critic ...`,
  { label: `coherence-critic:${id}#${round + 1}`, phase: 'Critic', agentType: 'qrspi-coherence-critic', schema: CRITIC_VERDICT_SCHEMA }) // :1667-1676 runCoherenceCritic
```

— `.claude/workflows/qrspi-batch.js:1243`, `:719-724`, `:816-823`, `:1667-1676`; `runSliceCritic` body at `:1718-1782`.

**Dependencies:** All call sites depend on the injected `agent`/`parallel`/`log` globals (Discovered Patterns). `runCriticPanelLoop` additionally wraps `agent()` calls inside `parallel(lenses.map(...))` (`:813-827`) — a wrapper must compose cleanly with `parallel`.
**Implicit contracts:** (1) Two positional args only. (2) `opts.label`/`opts.phase` always set — a wrapper can log against them without new params. (3) `schema` presence toggles return type (object vs string), but `null` is the uniform failure value regardless. (4) Inside `parallel()`, each `agent()` is an independent async thunk — a wrapper must be re-entrant / safe under concurrency.

## Q4: How does the `critics` config block get read (the "resolved-not-hard-coded" mechanism the ticket says to mirror for `retry`) — which function parses it, and what is its return shape and default-handling behavior?

**Answer:** Two layers, the canonical "resolved-not-hard-coded" pattern to mirror:

1. **Python tested core — `scripts/qrspi_critics_config.py`.** Self-locates the repo root from `__file__` (`REPO_ROOT = Path(__file__).resolve().parents[1]`), reads `.qrspi/config.json` ONCE via the shared `read_config()` (imported from `qrspi_config.py`), pulls the optional `critics` block, and emits a single-line JSON envelope `{ "ok": true, "phases": {<six resolved phases>}, "warnings": [...] }` (exit 0) or `{ "ok": false, "phases": {<all defaults>}, "warnings": [], "error": "..." }` (exit != 0). `phases` is ALWAYS present and complete. Pure resolvers (`resolve_critics`, `resolve_edge_phase`, `resolve_design`, `resolve_implementation`, `resolve_enabled`, `_pos_int_or`) take in-memory dicts and apply config-value > default precedence; defaults are uniform OFF (`enabled: false`) with `maxRounds: 2`. Unit-tested by `qrspi_critics_config_test.py`.

2. **JS thin glue — `readCriticsConfig(phaseLabel)` + `parseCriticsEnvelope(text)`.** A worker agent runs `python3 ${engineCmd('scripts/qrspi_critics_config.py')}` verbatim and returns its stdout text; `parseCriticsEnvelope` extracts the JSON, validates `phases` is a non-array object, logs each `warnings[]` entry, and shallow-merges over `DEFAULT_CRITIC_PHASES` (the JS-side fallback mirror). ANY failure (no JSON / parse error / missing phases) returns `DEFAULT_CRITIC_PHASES` so a garbled config NEVER gates the run.

For a NEW `retry` block, the established mirror would be: add a `resolve_retry(cfg)` pure resolver in a Python script (its own `scripts/qrspi_retry_config.py` or folded into the config envelope), a `_test.py` sibling, a JS `DEFAULT_RETRY` fallback constant, and a `parse...Envelope` that shallow-merges over the default.

**Evidence:**

```python
def resolve_enabled(cfg, default):
    cfg = cfg if isinstance(cfg, dict) else {}
    value = cfg.get("enabled")
    if value is True: return True
    if value is False: return False
    return default
```

— `scripts/qrspi_critics_config.py:87-101`

```js
function parseCriticsEnvelope(text) {
  const raw = extractJsonObject(text)
  if (!raw) return DEFAULT_CRITIC_PHASES
  let env
  try { env = JSON.parse(raw) } catch { return DEFAULT_CRITIC_PHASES }
  const phases = env && typeof env === 'object' ? env.phases : undefined
  if (!phases || typeof phases !== 'object' || Array.isArray(phases)) return DEFAULT_CRITIC_PHASES
  if (Array.isArray(env.warnings)) for (const w of env.warnings) log(`  config: ${w}`)
  return { ...DEFAULT_CRITIC_PHASES, ...phases }
}
```

— `.claude/workflows/qrspi-batch.js:369-378`; worker at `readCriticsConfig` `:1154-1169`; JS default at `DEFAULT_CRITIC_PHASES` `:612-619`.

**Dependencies:** `qrspi_critics_config.py` → `qrspi_config.read_config` (`scripts/qrspi_config.py:45-56`). JS glue → the injected `agent`/`log` globals + `extractJsonObject`.
**Implicit contracts:** (1) Python self-locates from `__file__` (never cwd/arg) — every `scripts/qrspi_*.py` follows this. (2) Envelope is ALWAYS complete (defaults on any failure) so JS never special-cases a missing field. (3) JS keeps a defaults mirror in lockstep with the Python defaults (comment at `:611` says "Keep this in lockstep"). (4) Only an explicit boolean flips `enabled`; non-bool ⇒ default — a `retry.enabled` flag should follow the same `resolve_enabled` idiom. (5) `qrspi_config.py` reads ONE top-level key only (no dot-path); a nested `critics`/`retry` block is read by the dedicated all-phases script, not `qrspi_config.py --key`.

## Q5: What label/identifier is associated with each `agent()` invocation (e.g. `[design:RUS-77]`) and how is it derived, so a retry log line can name the agent and attempt n/N?

**Answer:** Every `agent()` call passes an `opts.label` string, derived inline at the call site by template literal. Patterns observed:

- Phase producers: `` `${name}:${id}` `` ⇒ e.g. `questions:RUS-77`, `research:RUS-77`, `design:RUS-77` (`runPhase` `:1243`).
- Single critic: `` `critic:${id}:${name}#${round + 1}` `` ⇒ `critic:RUS-77:design#1` (`:724`).
- Panel lens: `` `critic:${id}:${name}:${lens}#${round + 1}` `` ⇒ `critic:RUS-77:design:simplicity#1` (`:823`).
- Reviser: `` `revise:${id}:${name}#${round + 1}` `` (`:762`, `:886`).
- Coherence: `` `coherence-critic:${id}#${round + 1}` `` (`:1676`).
- Workers: `` `persist:${id}:${name}` ``, `` `nodecheck:${id}:${name}` ``, `` `finalize-design:${t.id}` ``, `'config:critics'`, `` `critic-decision#${round}` ``, `` `slice-decide:${t.id}#${n}` ``.

The label is always available in `opts` at the seam, so a retry wrapper can read `opts.label` and append the attempt counter — e.g. `log(`  ${opts.label}: attempt ${n}/${N} ...`)` — matching the existing log style (see Q13). The `opts.phase` field (e.g. `'Critic'`, `'Design'`) is the coarser progress group.

**Evidence:**

```js
const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
```

— `.claude/workflows/qrspi-batch.js:1243`

```js
{ label: `critic:${id}:${name}:${lens}#${round + 1}`, phase: 'Critic', agentType, schema: CRITIC_VERDICT_SCHEMA }
```

— `.claude/workflows/qrspi-batch.js:823`

**Dependencies:** Labels are pure template-literal derivations of in-scope vars (`name`, `id`, `round`, `lens`) — no external lookup.
**Implicit contracts:** The label embeds round info via `#${round + 1}` (1-based) for critic loops; a retry attempt counter is an orthogonal axis (transient-failure retries within ONE round), so it should be a distinct suffix (e.g. `~attempt n/N`) to avoid colliding with the `#round` convention. `:id` segments are ticket ids; `name` is the artifact/phase name.

## Q6: After a propagated agent failure today, what state is left behind for the ticket (branches, artifacts, Linear status) — i.e. what must a retry leave unchanged so "ticket left untouched" holds after N exhausted attempts?

**Answer:** On a propagated phase-agent failure, NOTHING is mutated for the ticket beyond what completed before the failing step:

- **Artifacts:** Phase agents write to a TOKEN-FREE STAGING path `/tmp/phase-stage/<id>/<artifact>.md` (the `stg()` helper), NOT the canonical worktree path. Persist to the canonical `.worktrees/<id>/.qrspi/<id>/` happens ONLY after the producer + node-check + critic loop all succeed, via `persistArtifact` (`runPhase:1299`). A failure before persist leaves the canonical artifact absent/unchanged — `persist` is "the real success gate." So a failed phase leaves no canonical artifact for that phase.
- **Branches / PRs:** The finalize worker (commit + `gt submit`) runs only AFTER `runPhase` succeeds (e.g. `doDesign` finalize at `:1561-1567` runs after all three `runPhase` calls returned true). A failed phase returns `failTicket(t)` (`:1480`, `:1508`, `:1542`) BEFORE finalize, so no commit/branch/PR is created.
- **Linear status:** Status updates are best-effort and live in the finalize worker (per the PR-gated lifecycle: Linear is a "best-effort reporting projection"). A pre-finalize failure performs no Linear write.
- **Result record:** `failTicket` returns `{ action:'failed', summary:'A phase agent failed; ticket left untouched (no fabrication).' }` — its own summary asserts the invariant.

The resolver `scripts/qrspi_resolve_state.py` derives the next action purely from PR review state + existing artifacts on disk; it has no per-attempt state. So after N exhausted retries the ticket must look exactly as it did before the run started: no canonical artifact for the failing phase, no new branch/PR/commit, no Linear write. **A retry that exhausts must return `null` (preserving the Q1 contract) so `failTicket`/`skip` fire and this untouched state holds.**

**Evidence:**

```js
const stg = (id, name) => `/tmp/phase-stage/${id}/${name}.md`
```

— `.claude/workflows/qrspi-batch.js:629`

```js
  // The agent wrote to a token-free staging path; move it to the canonical worktree
  // path deterministically. This is also the real success gate ...
  const p = await persistArtifact(id, name, phaseLabel)
  if (!p || !p.ok) { log(...); return false }
```

— `.claude/workflows/qrspi-batch.js:1296-1303`

**Dependencies:** `runPhase` → `persistArtifact` → `scripts/qrspi_persist.py` (verifies staged file non-empty before moving). Finalize workers → `gt submit` (Graphite) + Linear MCP. Resolver `scripts/qrspi_resolve_state.py` reads PR state + `existing{}` artifact map, no attempt state.
**Implicit contracts:** "Fail toward untouched, never fabricate" — every failure path returns before any canonical/remote mutation. Staging+deterministic-move ("Fix A") guarantees a partial/failed phase persists nothing. A retry wrapper must NOT perform any mutation between attempts (the staged file from a failed attempt is overwritten or ignored, not committed).

## Q7: Is there existing per-run or per-attempt counter/iteration state in the critic loops that a retry-attempt counter should align with, or do those loops track only their own iteration bound?

**Answer:** The critic loops track ONLY their own ROUND iteration bound — a `for (let round = 0; round < maxRounds; round++)` whose `maxRounds` comes from config (default 2). This `round` counter is a CRITIC-CONVERGENCE axis (produce → critique → revise → re-critique), entirely distinct from a transient-failure RETRY axis. There is NO existing per-attempt / per-spawn retry counter anywhere — when any `agent()` inside a round returns `null`, the loop immediately returns `{ ok:false }` (NO retry). There is also no per-RUN counter threaded across tickets.

The convergence decision is delegated to the tested pure module `scripts/qrspi_critic_loop.py` (`next_action(verdicts, round, max_rounds)` via the `criticDecision` worker), which receives `round`/`max_rounds` but knows nothing about transient retries. A retry-attempt counter should therefore be a NEW, orthogonal inner loop (retry the single `agent()` spawn n/N times on a transient classification) nested INSIDE each round — it should NOT reuse or perturb `round`/`maxRounds`, and must leave `next_action`'s round accounting untouched.

**Evidence:**

```js
async function runCriticLoop(name, id, criticConfig) {
  const maxRounds = criticConfig.maxRounds ?? 2
  ...
  for (let round = 0; round < maxRounds; round++) {
    const verdict = await agent(...)
    if (verdict === null) { ...; return { ok: false, residualFindings: [] } }   // no retry today
    ...
    const decision = await criticDecision([verdict], round, maxRounds)
```

— `.claude/workflows/qrspi-batch.js:710-736`; panel `:801-810`; coherence `:1664` (`for (let round = 0; round < rounds; round++)`); slice critic `:1718`.

**Dependencies:** Round decision → `scripts/qrspi_critic_loop.py` `next_action` (tested by `qrspi_critic_loop_test.py`).
**Implicit contracts:** `round` is 1-based in labels (`#${round + 1}`), 0-based in the loop and in `next_action`. `maxRounds` defaults to 2 (`?? 2` in JS, `DEFAULT_MAX_ROUNDS = 2` in Python). A retry counter is a separate dimension; aligning it with `round` would corrupt convergence accounting.

## Q8: How are the explicitly non-retryable signatures `monthly spend limit` and dirty-tree / `trunk sync failed` surfaced in the current run output — what exact strings appear, so the default-deny classifier can be tested against the must-NOT-retry cases?

**Answer:** Two distinct mechanisms; neither is an `agent()` failure:

- **`monthly spend limit`:** NOT FOUND in code (see Q2). No string/field for it exists in-repo; it is a harness-runtime message, not surfaced through any in-repo path. The "must-NOT-retry" test for it cannot anchor on an existing in-repo string — the classifier would have to be fed the literal harness message as a test fixture.

- **Trunk-sync / dirty-tree:** These are NOT `agent()` failures — they come from the deterministic Python script `scripts/qrspi_sync_trunk.py`, whose pure `classify_sync(...)` returns one of the tokens `"updated" | "already-current" | "not-on-main" | "dirty" | "fetch-failed" | "divergent"`, and `build_envelope(...)` produces the exact `error` strings:
  - dirty tree: `"main working tree dirty + porcelain lines:\n%s"`
  - not on main: `"main checkout HEAD is not on 'main' (on %s); refusing FF-only sync"`
  - fetch failed: `"git fetch origin failed, %s"`
  - divergent: `"local main diverged from origin/main; not fast-forwardable"`
  These surface in the JS as a thrown Error that ABORTS the whole run (fail-loud), NOT a per-ticket retry: `throw new Error(`run-start trunk sync failed — ${runStartSync.error ?? 'unknown'}; aborting run ...`)` (`:2548`) and the post-land equivalent (`:2245`). The literal substring `trunk sync failed` appears ONLY in those two JS throw messages.

So the testable must-NOT-retry anchors are the `qrspi_sync_trunk.py` envelope `error` strings (tested by `qrspi_sync_trunk_test.py`) and the two JS `... trunk sync failed — ...; aborting run` throw messages. `monthly spend limit` has no in-repo string at all.

**Evidence:**

```python
    if token == "dirty":
        return { "ok": False, ..., "error": "main working tree dirty + porcelain lines:\n%s" % dirty_porcelain }
    if token == "fetch-failed":
        return { "ok": False, ..., "error": "git fetch origin failed, %s" % fetch_detail }
    if token == "divergent":
        return { "ok": False, ..., "error": "local main diverged from origin/main; not fast-forwardable" }
```

— `scripts/qrspi_sync_trunk.py:99-115` (classifier tokens at `:47-71`)

```js
  throw new Error(`run-start trunk sync failed — ${runStartSync.error ?? 'unknown'}; aborting run (refusing to build on a stale local main)`)
```

— `.claude/workflows/qrspi-batch.js:2548` (post-land twin at `:2245`)

**Dependencies:** `qrspi_sync_trunk.py` (`classify_sync`/`build_envelope`) ← `parseSyncTrunkEnvelope` (JS) ← run-start/post-land sync guards. Trunk-sync failure is a RUN-LEVEL `throw`, separate from per-ticket `agent()` failures.
**Implicit contracts:** Trunk-sync failure is fail-LOUD and ABORTS the run — it is categorically NOT an `agent()` retry candidate (it never flows through `agent()`/`null`). The classifier's default-deny set must NOT match these strings, but they are also out of the retry wrapper's reach entirely (different code path). `monthly spend limit` must be encoded in the default-deny list from the literal harness text, with no in-repo string to test against — flagged in Inconsistencies.

## Q9: Do any of the listed transient signatures (`429`, `529`, `ECONNRESET`, `terminated`, `fetch failed`, `socket connection was closed unexpectedly`) overlap textually with non-retryable messages or with substrings that could cause a false-positive allowlist match?

**Answer:** NOT FOUND as an existing classifier (the transient classifier is a NEW pure module per the questions' Target). Analyzing textual overlap against the in-repo non-retryable strings (Q8):

- **`fetch failed` vs `"git fetch origin failed, ..."`:** HIGH false-positive risk. The trunk-sync dirty/fetch error contains `fetch ... failed`, and a naive substring/case-insensitive `fetch failed` allowlist token could match the non-retryable `"git fetch origin failed"`. However, trunk-sync errors travel a DIFFERENT path (a run-level `throw`, not an `agent()` null — Q8), so they would not reach the wrapper IF the wrapper only sees `agent()` results. The risk is real only if the classifier is applied to arbitrary error text rather than scoped to the `agent()` seam.
- **`terminated`:** generic word; could appear in unrelated messages (e.g. "process terminated", git output). Moderate false-positive risk against arbitrary text.
- **`429` / `529`:** bare 3-digit numbers; could match substrings of unrelated numbers (e.g. a SHA, a byte count `529B`, a line number). The persist log line literally prints byte counts (`saved ${p.bytes}B`). A naive numeric-substring match is risky; anchor to "429"/"529" with HTTP-status context.
- **`ECONNRESET`, `socket connection was closed unexpectedly`:** distinctive, low overlap with in-repo strings.
- **`monthly spend limit`** (non-retryable) does NOT textually overlap any transient token — good (they are mutually exclusive substrings).

No EXISTING classifier exists to inspect, so this is a design-time analysis: the dominant collision is `fetch failed` ⊂ `git fetch origin failed`, plus loose numeric matches for `429`/`529`. Mitigation patterns already in the repo: the resolver/config use exact-token / structured matching, not loose substring (e.g. `classify_sync` returns enum tokens, never substring-matches free text).

**Evidence:**

```python
        return { ..., "error": "git fetch origin failed, %s" % fetch_detail }
```

— `scripts/qrspi_sync_trunk.py:109` (the `fetch failed` substring collision source)

```js
  log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
```

— `.claude/workflows/qrspi-batch.js:1304` (a numeric-substring collision source for bare `429`/`529`)

**Dependencies:** No existing classifier module under `scripts/` (NOT FOUND — searched `scripts/*retry*`, `*transient*`, `*classif*`: none). The new module is greenfield.
**Implicit contracts:** Default-DENY (only an explicit transient match retries; everything else, including unknown/non-retryable, fails immediately). Substring matching on free-form error text is the false-positive vector; the codebase convention favors exact enum tokens over loose substring tests.

## Q10: Is there an existing backoff/sleep/jitter utility in the codebase (Python or JS) that the bounded exponential-backoff-with-jitter requirement can reuse, or must the delay be implemented anew?

**Answer:** NOT FOUND — there is NO existing backoff/sleep/jitter/delay utility in either language. Searched `.claude/workflows/qrspi-batch.js` for `setTimeout`, `sleep`, `delay`, `jitter`, `backoff`, `Promise`, `await new` — ZERO hits. Searched `scripts/` filenames for `backoff|retry|sleep|jitter` — none. The JS workflow has no timer/delay primitive in use; the harness-injected globals are `agent`, `parallel`, `pipeline`, `phase`, `log`, `args` (per `docs/testing-dynamic-workflows.md:34-40`), and whether `setTimeout`/`Promise` are available in the workflow sandbox is NOT documented (the doc confirms NO fs / `import` / `process`, but does not state timer availability).

The bounded exponential-backoff-with-jitter delay must therefore be implemented anew. Two seams per the Functional-Core/Imperative-Shell pattern the repo follows:
- The pure DELAY-COMPUTATION (attempt n ⇒ delay ms with exponential base + jitter + cap) belongs in a tested Python module (`scripts/qrspi_*.py` + `_test.py`), mirroring how all decision logic lives in Python.
- The actual SLEEP (the side-effecting wait) is the imperative-shell part in JS — but the sandbox's timer capability is unverified (open question), so the design must confirm how to sleep in the workflow sandbox (e.g. `await new Promise(r => setTimeout(r, ms))` if `setTimeout` exists, or a worker-agent that sleeps).

**Evidence:**

```
$ grep -n "setTimeout|sleep|delay|jitter|backoff|Promise|await new" .claude/workflows/qrspi-batch.js
# (no matches)
$ ls scripts/ | grep -iE "backoff|retry|sleep|jitter"
# (no matches)
```

Injected globals enumerated (no timer listed):

> `agent()`, `parallel()`, `pipeline()`, `phase()`, `log()`, `args`, `budget`, `workflow()`.

— `docs/testing-dynamic-workflows.md:34-40` (note: `budget`/`workflow()` are listed there but grep finds NO usage of them in `qrspi-batch.js`)

**Dependencies:** None to reuse — greenfield.
**Implicit contracts:** Per the repo's TDD strategy (`docs/testing-dynamic-workflows.md:109-114`), any NEW deterministic logic (the delay schedule) goes in a tested `scripts/*.py` helper, NOT inlined as nontrivial JS. The sleep side-effect is the residual untestable shell seam. Sandbox timer availability is UNVERIFIED — flagged in Inconsistencies.

## Q11: What is the structure of an existing pure-classifier-style test (e.g. `scripts/qrspi_resolve_state_test.py`) and how does `scripts/run_tests.py` discover and run `scripts/*_test.py`, so the new classifier test slots into the suite and CI?

**Answer:** **Test structure** (canonical, e.g. `qrspi_critic_loop_test.py`): a stdlib-only, assert-based script with NO pytest / no test runner / no third-party deps. It (1) inserts its own dir on `sys.path` (`sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))`), (2) imports the pure functions under test from the sibling module, (3) defines a `check(label, got, want)` helper that increments `total`/`failures` and prints `ok:`/`FAIL:`, (4) calls `check(...)` for each case, (5) exits non-zero iff `failures` (an `if __name__ == "__main__": sys.exit(1 if failures else 0)` style). Run directly: `python3 scripts/<name>_test.py`.

**Discovery / CI:** `scripts/run_tests.py` `discover_tests()` lists every `scripts/*_test.py` (sorted, optional substring filter), and `run_one()` runs each as its OWN subprocess (`subprocess.run([python, path], ...)`, 180s timeout), counting exit-0 as pass. `run_suite()` prints per-file PASS/FAIL + aggregate, and `main()` returns 1 if any failed. CI gate: `.github/workflows/tests.yml` runs `python3 scripts/run_tests.py` on every PR + push to `main`. So a NEW `scripts/qrspi_<classifier>_test.py` is auto-discovered with ZERO registration — just name it `*_test.py` and place it in `scripts/`.

**Evidence:**

```python
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from qrspi_critic_loop import (next_action, parse_critic_verdict)
failures = 0; total = 0
def check(label, got, want):
    global failures, total
    total += 1
    if got == want: print("ok: %s" % label)
    else: failures += 1; print("FAIL: %s\n   got:  %r\n   want: %r" % (label, got, want))
```

— `scripts/qrspi_critic_loop_test.py:14-36`

```python
def discover_tests(scripts_dir=SCRIPT_DIR, pattern=None):
    names = sorted(n for n in os.listdir(scripts_dir) if n.endswith("_test.py"))
    if pattern: names = [n for n in names if pattern in n]
    return [os.path.join(scripts_dir, n) for n in names]
```

— `scripts/run_tests.py:36-48`; subprocess runner `:51-75`; CI gate `.github/workflows/tests.yml`.

**Dependencies:** `run_tests.py` (no deps) ← CI `.github/workflows/tests.yml`. Each test ← its sibling pure module.
**Implicit contracts:** (1) Test file MUST end `_test.py` and live in `scripts/` to be discovered. (2) MUST exit non-zero on failure (subprocess return code is the only signal). (3) Stdlib-only, self-contained. (4) `run_tests.py` itself and its own test are handled specially (`run_tests_test.py` is a normal member; `run_tests.py` is excluded by not ending `_test.py`). (5) Per-file 180s timeout — a hung test fails.

## Q12: What is the JS↔Python contract-fixture pattern referenced for verifying the harness-coupled wrapper, and where are its existing fixtures defined?

**Answer:** The PATTERN is documented in `docs/testing-dynamic-workflows.md` as strategy item 3, "Contract / golden fixtures at the JS↔Python seam": capture a real Python-script output envelope as a committed fixture, then assert BOTH sides against it — Python tests that the script PRODUCES the envelope, JS tests that the parser CONSUMES it (consumer-driven contract + record/replay on the internal seam, fully deterministic, no LLM). The JS parsers (`parseResolveEnvelope`, `parseSyncTrunkEnvelope`, `parseConfigEnvelope`, `parseCriticsEnvelope`, `extractJson*`, …) are the consumer side; their Python producers are already tested (`qrspi_sync_trunk_test.py`, `qrspi_config_test.py`, `qrspi_critics_config_test.py`, etc.).

**Existing fixtures: NOT FOUND.** There is NO `scripts/fixtures/` directory and NO `*contract*` test file (searched `scripts/*contract*`, `scripts/fixtures/`: none). The doc explicitly marks this item as aspirational — *"(Tracked as a QRSPI ticket.)"* (`:131`) — and `docs/testing-dynamic-workflows.md` is labeled *"research synthesis + recommended strategy"* (`:9`), not an implemented harness. The companion MEMORY note ("Testing dynamic workflow scripts") confirms the JS shell is harness-coupled and the residual JS seam is to be covered by "JS↔Python contract fixtures" — a recommended-but-not-yet-built approach. The doc also confirms (RESOLVED 2026-06-14 experiment) that the workflow sandbox supports NO `require`/`import`/fs, so JS-side coverage must use a `node:vm` sandbox evaluating the source with stubbed globals, or push parsing into Python.

**Evidence:**

> **(Strongest repo-specific fit) Contract / golden fixtures at the JS↔Python seam.** Capture real Python-script output envelopes as committed fixtures, and assert **both** sides against them: Python tests that the script *produces* the envelope, JS tests that the parser *consumes* it. ... *(Tracked as a QRSPI ticket.)*

— `docs/testing-dynamic-workflows.md:124-131`

> *vm-sandbox tests (likely path):* test parsers via a `node:vm` sandbox that evaluates the file source with stubbed globals. Note: top-level `const`/arrow helpers do **not** attach to the vm context (only `function` declarations and `var` do), so you must append an export shim to the source before evaluating.

— `docs/testing-dynamic-workflows.md:138-141`

**Dependencies:** Doc references the producer tests (`qrspi_sync_trunk_test.py`, `qrspi_config_test.py`, `qrspi_critics_config_test.py`, `qrspi_resolve_state_test.py`, `qrspi_land_verify_test.py`) as the already-tested producer side.
**Implicit contracts:** A harness-coupled wrapper (the retry seam in `qrspi-batch.js`) CANNOT be unit-tested directly (no `import`, top-level `return`, injected globals). The recommended path: put the delay/classification LOGIC in tested Python, keep the JS wrapper a thin logic-free shell, and (if JS coverage is wanted) cover the residual parse seam via vm-sandbox or contract fixtures that do not yet exist. **The fixture infrastructure must be built, not reused.**

## Q13: What logging mechanism do `runPhase` and the critic loops currently use to emit run progress (function, stream, format), so each retry attempt's log line (agent label, attempt n/N, classified signature, delay) matches the existing format and is captured in run output?

**Answer:** All progress is emitted via the harness-INJECTED global `log(...)` (a single-string call; not `console.log`, not defined in the file — 99 call sites). The convention is a two-space-indented, ticket-prefixed line: `` log(`  ${id}: <message>`) `` (the critic loops add the artifact name, round, and PASS/FAIL/REVISE/CAP-REACHED state). `phase('<Name>')` (also injected) sets the coarser progress group. There is no separate stderr/stdout choice exposed — `log()` is the only sink and the workflow runtime captures it into the run output.

A retry attempt's log line should reuse `log()` with the same `  ${label}: ...` shape — e.g. `` log(`  ${opts.label}: transient failure (<signature>), retry ${n}/${N} after ${delay}ms`) `` — so it interleaves with the existing per-round critic lines and is captured identically. The `opts.label` (Q5) provides the agent/ticket identity; the attempt n/N, classified signature, and delay are the new fields.

**Evidence:**

```js
log(`  ${id}: ${name} critic round ${round + 1}/${maxRounds} → ${passed ? 'PASS' : `FAIL (${findings.length} finding(s))`}`)
...
log(`  ${id}: ${name} critic REVISE at round ${round + 1} — rewriting artifact to address findings`)
```

— `.claude/workflows/qrspi-batch.js:732`, `:753`

```js
log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
```

— `.claude/workflows/qrspi-batch.js:1304` (runPhase success line)

**Dependencies:** `log` / `phase` injected globals (per `docs/testing-dynamic-workflows.md:34-40`). No logging library, no levels, no streams.
**Implicit contracts:** (1) `log()` takes ONE pre-formatted string. (2) Two-space indent + `${id}:` prefix for per-ticket lines; `config: ...` prefix for config worker warnings (`:376`). (3) No log levels — severity is conveyed in the message text (PASS/FAIL/CAP-REACHED). (4) The label format `<role>:<id>[:<name>][#<round>]` (Q5) is the identity convention a retry line should echo.

---

## Discovered Patterns

- **Functional Core / Imperative Shell is the load-bearing architecture.** Every deterministic decision lives in a tested, self-locating Python module (`scripts/qrspi_*.py` with a `_test.py` sibling) that derives `REPO_ROOT` from `__file__` (two levels up) and prints a single-line JSON envelope; `qrspi-batch.js` is a thin shell that shells out to it via a worker agent and parses the envelope. This is explicitly mandated (`docs/testing-dynamic-workflows.md:109-114`). A new retry feature's LOGIC (delay schedule, transient classification, retry config resolution) should follow this — Python core + JS glue.
- **Uniform `agent()` failure contract = `null`.** ~20 call sites, all `await agent(prompt, { label, phase, agentType?, schema? })`, all treating `null`/falsy/non-`ok` as "stop this ticket, fabricate nothing." No exception path is observed. This is the single seam a retry wrapper interposes on.
- **Staging + deterministic move ("Fix A")** ensures a failed phase persists nothing canonical (`stg()` → `qrspi_persist.py`), so "ticket left untouched" is structural, not best-effort.
- **Config envelopes always complete + default-on-failure.** `qrspi_config.py` (one key) and `qrspi_critics_config.py` (all phases) both emit a fully-populated `phases`/`value` even on error; JS keeps a defaults mirror (`DEFAULT_CRITIC_PHASES`) "in lockstep." A `retry` block should mirror this exactly.
- **Default-deny / fail-toward-blocking is the repo's safety posture** (resolver blocker classification, critic null-handling, trunk-sync fail-loud). A transient-error classifier defaulting to deny (retry only on explicit match) is idiomatic here.
- **Labels are inline template literals** of the form `<role>:<id>[:<name>][:<lens>][#<round+1>]`; rounds are 1-based in labels, 0-based in loops.
- **Run-level fail-loud `throw` vs per-ticket `null`-to-`skip`/`failTicket` are two separate failure regimes.** Trunk-sync failures `throw` and abort the entire run; phase-agent failures return `null` and abort only that ticket. A retry wrapper belongs in the SECOND regime only.

## Inconsistencies

- **Q2/Q8 core gap: the error SIGNATURE the feature wants to classify is NOT available at the current `agent()` seam.** `agent()` returns only `null` on failure (no message, no code). The transient signatures (`429`, `socket connection was closed unexpectedly`, etc.) and the non-retryable `monthly spend limit` appear NOWHERE in the repo — they are harness-runtime strings. The questions assume an inspectable signature exists; today it does not flow through to the JS. The design MUST specify how the wrapper obtains the error text (e.g. whether `agent()` throws a message before/instead of returning `null`, requiring a `try/catch`), because the present return contract discards it. This is the single biggest unknown for the feature.
- **`fetch failed` (retryable token) is a textual substring of `"git fetch origin failed, ..."` (non-retryable trunk-sync error).** A loose substring classifier would false-positive. They travel different code paths (run-level `throw` vs `agent()` null), so scoping the classifier to the `agent()` seam avoids the collision — but a free-text classifier applied broadly would not. Bare `429`/`529` similarly risk matching unrelated numbers (e.g. the `saved <bytes>B` log line). Use exact/anchored tokens, per the repo's enum-token convention.
- **No delay/timer primitive and unverified sandbox timer support.** No backoff/sleep/jitter utility exists (Q10), and `docs/testing-dynamic-workflows.md` confirms the workflow sandbox has no fs/`import`/`process` but does NOT confirm `setTimeout`/`Promise` availability. The sleep mechanism is an open design question.
- **`docs/testing-dynamic-workflows.md` lists `budget` and `workflow()` as injected globals (`:34-40`), but `qrspi-batch.js` uses NEITHER** (grep finds zero usage). The doc's global list is broader than this file's actual usage — do not assume `budget`/`workflow()` are available for a retry-budget feature without verifying with the harness.
- **The JS↔Python contract-fixture infrastructure (Q12) is recommended but NOT built** — no `scripts/fixtures/`, no contract test. The doc marks it "(Tracked as a QRSPI ticket.)". Verifying the harness-coupled retry wrapper on the JS side requires building this (or a `node:vm` shim) first; only the Python core can be unit-tested with the existing `run_tests.py` harness today.
