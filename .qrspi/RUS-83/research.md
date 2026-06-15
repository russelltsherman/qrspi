# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft

## Q1: How does the `CI-Revise-Attempt: N` head-commit trailer get written, read back, and surfaced into the resolver's input, and where in that path is the count derived as an integer?

**Answer:** The trailer is a full round trip across three modules. **Write:** the revise worker (an LLM agent prompt inside `doRevise` in `qrspi-batch.js`) is instructed to set exactly one `CI-Revise-Attempt: <value>` trailer on the head commit via a message-only `gt modify --no-interactive -m "..."` AFTER the content amend. There is no Python/JS code that writes the trailer — it is a natural-language instruction to the worker (the content amender `qrspi_revise_amend.py` preserves the message verbatim and cannot write it). **Read:** `ci_revise_attempt(message)` in `qrspi_pr_state.py:115-130` parses the head-commit message with a regex and returns an int (the integer derivation point). **Surface:** `parse_pr_state` (`qrspi_pr_state.py:303-321`) calls it only when `ciState == "red"` and emits the int as the `ciReviseAttempt` field on the per-PR shape; the resolver reads that field via `ci_revise_attempt_of` (`qrspi_resolve_state.py:129-138`).

**Evidence:**

```python
_CI_REVISE_ATTEMPT_RE = re.compile(r"^CI-Revise-Attempt:\s*(\d+)\s*$", re.MULTILINE)

def ci_revise_attempt(message):
    matches = _CI_REVISE_ATTEMPT_RE.findall(message or "")
    if not matches:
        return 0
    try:
        return int(matches[-1])      # last occurrence wins; integer derived here
    except (TypeError, ValueError):
        return 0
```

— `scripts/qrspi_pr_state.py:112-130`

```javascript
   d. Apply it as a message-only amend (NO file changes): `gt modify --no-interactive -m "<the full rewritten message>"`.
```

— `.claude/workflows/qrspi-batch.js:2323` (worker prompt — the only trailer-write mechanism)

**Dependencies:** `doRevise` (writer, via worker) → git head commit → `ci_revise_attempt` (`qrspi_pr_state.py`, reader) → `parse_pr_state` → resolver `ci_revise_attempt_of`. The cap value flows separately from config via `qrspi_resolve.py:464`.
**Implicit contracts:** The trailer is the *only* durable, GitHub-observable store of the counter — there is no on-disk state. The write is delegated to an LLM worker (no deterministic code enforces it). `re.MULTILINE` + last-wins mirrors git trailer semantics.

## Q2: When a revise worker reports failure and pushes no change, what (if anything) currently updates the PR's head commit, and does the trailer value the next batch run reads stay unchanged in that case?

**Answer:** Nothing updates the head commit on a failed-no-change revise. The trailer increment in `doRevise` is bundled into the worker prompt's content-fix flow (steps amend → write trailer → re-request review, `qrspi-batch.js:2315-2324`). The prompt explicitly tells the worker to SKIP the content amend when nothing changed (`qrspi-batch.js:2317` "If the prior step determined nothing further needs changing, SKIP the content amend") and to return `ok:false` with a verbatim reason if it could not address the failure (`qrspi-batch.js:2326`). The trailer write at step 6 is "For EACH branch you touched in this pass" — if no branch was touched and the worker returns failure, no `gt modify -m` runs. `finResult` (`qrspi-batch.js:2557-2563`) maps `ok:false` to a recorded failure result but performs NO commit mutation. So the head commit (and its `CI-Revise-Attempt: N`) is byte-for-byte unchanged, and the next batch run's gather reads the same N. **This is the non-progressing loop: a red frontier with a failing worker keeps re-emitting `revise` at the same attempt count.**

**Evidence:**

```javascript
${ciFailing ? '6' : '5'}. WRITE THE `CI-Revise-Attempt` TRAILER ... For EACH branch you touched in this pass ...
```

— `.claude/workflows/qrspi-batch.js:2318` (trailer write is gated on "branch you touched")

```javascript
function finResult(t, fin, action) {
  if (!fin || !fin.ok) {
    log(`  ${t.id}: ${action} finalize failed — ${fin?.error ?? fin?.summary ?? 'no result'} (nothing advanced)`)
    return { ticketId: t.id, action, summary: `${action} finalize failed: ...` }
  }
```

— `.claude/workflows/qrspi-batch.js:2557-2561` (failure path mutates no commit)

**Dependencies:** worker outcome → `finResult` → `results.push`. No path back to the trailer on failure.
**Implicit contracts:** Counter advancement is coupled to a *successful content amend* by the worker. There is no orchestrator-side trailer write that fires independently of worker success. (Directly relevant to Q8/Q11.)

## Q3: What is the signature and return shape of the revise worker invocation, and does it currently report a success/failure outcome back to the orchestrator?

**Answer:** `async function doRevise(t, r)` (`qrspi-batch.js:2231`). `t` is the ticket, `r` the resolver envelope (carries `r.decision`, `r.commentTargets`, `r.ciFailing`, `r.ciFailingChecks`, `r.worktreeDir`). It spawns a worker `agent(...)` with `WORKER_SCHEMA` (`qrspi-batch.js:2303-2328`). The worker DOES report a success/failure outcome: the prompt requires it to `Return: ok, prUrl, newStatus, summary ... if you could not address the failure/feedback, return ok:false with the verbatim reason` (`qrspi-batch.js:2326`). That result is run through `finResult(t, fin, 'revise:' + d.phase)` (`qrspi-batch.js:2329`). **However, the orchestrator does NOT branch on the ok/false to advance any attempt counter** — `finResult` only logs and shapes a result record. So the outcome is *captured and logged* but never *fed back into the counter*.

**Evidence:**

```javascript
  const out = finResult(t, fin, `revise:${d.phase}`)
  if (out && commentSummary) {
    out.summary = `${out.summary || ''} Also ${commentSummary}.`.trim()
  }
  return out
```

— `.claude/workflows/qrspi-batch.js:2329-2333`

**Dependencies:** `doRevise` → `agent`/`WORKER_SCHEMA` → `finResult` → returned to the dispatch switch (`qrspi-batch.js:2883`) → `results.push(res)` (`qrspi-batch.js:2891`).
**Implicit contracts:** The worker is honesty-bound to return `ok:false` on failure (`qrspi-batch.js:2307`, `2326`). The orchestrator treats `revise` as best-effort: a failed revise is recorded, the run proceeds, and nothing else changes for that ticket this pass.

## Q4: What fields does the gather emit for CI state and what is the exact JSON contract consumed by `qrspi_resolve_state.py`?

**Answer:** `parse_pr_state` (`qrspi_pr_state.py:290-321`) emits three additive CI fields on the per-PR shape: `ciState` (one of `green|red|pending|none` from `check_rollup_state`, `qrspi_pr_state.py:89-109`), `ciFailingChecks` (a list of `{name, detailsUrl}`, populated only when red, from `_failing_checks`, `qrspi_pr_state.py:133-156`), and `ciReviseAttempt` (the effective int counter — the parsed trailer forced to 0 unless red). The no-PR sentinel sets `ciState:"none", ciFailingChecks:[], ciReviseAttempt:0` (`qrspi_pr_state.py:296`). The resolver consumes `ciState` (via `ci_state`, `qrspi_resolve_state.py:110-126`) and `ciReviseAttempt` (via `ci_revise_attempt_of`, `qrspi_resolve_state.py:129-138`) off each phase's PR dict in `state["phases"]`.

**Evidence:**

```python
    ci_state = check_rollup_state(node)
    failing = _failing_checks(node) if ci_state == "red" else []
    if ci_state == "red":
        attempt = ci_revise_attempt(_head_commit(node).get("message"))
    else:
        attempt = 0
    return {
        ... "ciState": ci_state, "ciFailingChecks": failing, "ciReviseAttempt": attempt,
    }
```

— `scripts/qrspi_pr_state.py:303-321`

**Dependencies:** `check_rollup_state`, `_failing_checks`, `ci_revise_attempt` (all in `qrspi_pr_state.py`) → the per-PR dict → resolver helpers.
**Implicit contracts:** `ciFailingChecks` is non-empty ONLY when `ciState=="red"`; `ciReviseAttempt` is the EFFECTIVE count (already not-red→0 reset at gather). The resolver reads it directly, "never re-zeroed" (`qrspi_resolve_state.py:131-132`).

## Q5: Where does the consecutive-red counter live as the source of truth, and how is the "effective count" computed when the resolver compares it against `ciReviseCap`?

**Answer:** The source of truth is the **head-commit trailer only** — there is no on-disk state (confirmed: no file read in the gather; the gather reads it from the GraphQL head-commit message at `qrspi_pr_state.py:306`). The "effective count" is computed in two stages: (1) **gather-side** — `ciReviseAttempt` is the parsed trailer int, but forced to 0 whenever `ciState != "red"` (`qrspi_pr_state.py:305-308`); (2) **resolver-side** — `ci_revise_attempt_of(phases, name)` reads that field directly, and for `implementation` aggregates across slices with `max(...)` (`qrspi_resolve_state.py:135-138`). The cap comparison is `attempt < ci_revise_cap` in `resolve` (`qrspi_resolve_state.py:291`). The cap itself is passed in by `qrspi_resolve.py` via `load_ci_revise_cap` reading the flat `ciReviseCap` key from `.qrspi/config.json` (`qrspi_resolve.py:363-369, 464-465`), defaulting to 3.

**Evidence:**

```python
def ci_revise_attempt_of(phases, name):
    if name == "implementation":
        attempts = [int(s.get("ciReviseAttempt", 0) or 0) for s in _impl_slices(phases)]
        return max(attempts) if attempts else 0
    return int(phases.get(name, {}).get("ciReviseAttempt", 0) or 0)
```

— `scripts/qrspi_resolve_state.py:129-138`

**Dependencies:** trailer (git) → `ci_revise_attempt` → `parse_pr_state.ciReviseAttempt` → `ci_revise_attempt_of` → cap compare in `resolve`. Cap: `.qrspi/config.json` → `load_ci_revise_cap` → `resolve(..., ci_revise_cap=)`.
**Implicit contracts:** The resolver is PURE — it does no disk read and trusts the gathered effective count (`qrspi_resolve_state.py:178-181`). The cap is threaded as an argument, never hard-coded in `resolve`.

## Q6: What are the two existing counter resets, and at what point in each path does the reset to `CI-Revise-Attempt: 0` occur?

**Answer:** (1) **Read-side gather reset** — in `parse_pr_state`, `ciReviseAttempt` is set to 0 whenever `ciState != "red"` (`qrspi_pr_state.py:305-308`). This makes the *effective* count 0 the moment CI goes non-red, regardless of the stale trailer value sitting on the commit. (2) **Writer-side `doRevise` reset** — when the revise is a NON-CI amend (comment-only path: `!changeRequested && !ciFailing`, and a comment was actually applied), `doRevise` calls `resetCiReviseTrailer(t, r, d, answered)` which spawns a worker to overwrite the trailer to `CI-Revise-Attempt: 0` on the amended branch(es) (`qrspi-batch.js:2276-2278`, helper at `2410-2436`). It occurs only when `answered.some(a => a.applied)` (an amend actually happened). In the change-request/CI branch, the path-dependent worker prompt sets the value to 0 on the "NON-CI amend" path (`qrspi-batch.js:2321`).

**Evidence:**

```python
    if ci_state == "red":
        attempt = ci_revise_attempt(_head_commit(node).get("message"))
    else:
        attempt = 0          # read-side not-red->0 reset
```

— `scripts/qrspi_pr_state.py:305-308`

```javascript
    if (answered.some(a => a.applied)) {
      await resetCiReviseTrailer(t, r, d, answered)   // writer-side reset to 0
    }
```

— `.claude/workflows/qrspi-batch.js:2276-2278`

**Dependencies:** read-side: `check_rollup_state` → the if/else. writer-side: `doRevise` → `resetCiReviseTrailer` (`qrspi-batch.js:2421-2434`, a `gt modify -m` worker).
**Implicit contracts:** The writer-side reset is "durability/observability hygiene on the committed head, not a correctness gate for the cap" (`qrspi-batch.js:2273-2275`) — the read-side reset is what actually governs the cap. The reset is best-effort (a failure WARNs, does not fail the revise — `qrspi-batch.js:2417`, `2436`).

## Q7: How does the resolver decide red → `revise` vs red → `wait` at the cap boundary today, and which value is the comparison made against?

**Answer:** In step 2c (`qrspi_resolve_state.py:287-301`), the frontier (highest existing phase) CI is evaluated. If `fci == "red"`, it reads `attempt = ci_revise_attempt_of(phases, frontier)` and compares `attempt < ci_revise_cap`: under cap → `decision("revise", ..., ciFailing=True)`; at/above cap → `decision("wait", ..., ciFailing=True)`. The comparison is made against the **effective (gathered) count** — the prior count as stored in the trailer (already not-red→0 normalized), NOT an incremented value. The resolver does not increment; it reads the count the worker last wrote and parks once that stored count reaches the cap.

**Evidence:**

```python
    fci = ci_state(phases, frontier)
    if fci == "red":
        attempt = ci_revise_attempt_of(phases, frontier)
        if attempt < ci_revise_cap:
            return decision("revise", phase=frontier, ciFailing=True, ...
                            reason="%s frontier PR has failing CI (attempt %d/%d); ..." % (...))
        return decision("wait", phase=frontier, ciFailing=True,
                        reason="%s frontier PR still has failing CI after %d/%d "
                               "consecutive auto-revise attempt(s); cap reached, parked ...")
```

— `scripts/qrspi_resolve_state.py:288-301`

**Dependencies:** `ci_state`, `ci_revise_attempt_of`, `decision` (all `qrspi_resolve_state.py`).
**Implicit contracts:** The comparison value is the *prior stored* attempt, so the cap is effectively reached only after a *successful* trailer write advanced it (see Q2/Q8 — a worker that never writes leaves the count stuck below cap forever). Step 2c runs AFTER the unified-feedback handler (2b) and BEFORE the active-phase block (`qrspi_resolve_state.py:273-281`).

## Q8: On a red frontier where the worker reports failure with no commit pushed, does the trailer get incremented at all, and if not, what is the observable state the next batch run reads?

**Answer:** No — the trailer is NOT incremented when the worker reports failure with no commit. As established in Q2, the trailer write (`qrspi-batch.js:2318-2323`) is conditioned on the worker having touched a branch and is part of the same prompt flow as the content amend; a worker that diagnoses but cannot fix returns `ok:false` (`qrspi-batch.js:2326`) without running the `gt modify -m`. The next batch run's gather re-reads the SAME head commit, parses the SAME `CI-Revise-Attempt: N` (still red, so not zeroed), and the resolver again computes `attempt == N < cap` → emits `revise` again. **This is exactly the non-progressing loop: the cap never advances because nothing ever increments the count on a failed attempt.** The observable state is: red CI + unchanged trailer + recurring `revise` decision (or `revise:... finalize failed` recorded each run).

**Evidence:**

```javascript
${ciFailing ? '5' : '4'}. When you made edits, stage them AND amend ... (If the prior step
determined nothing further needs changing, SKIP the content amend ...)
${ciFailing ? '6' : '5'}. WRITE THE `CI-Revise-Attempt` TRAILER ... For EACH branch you touched in this pass ...
```

— `.claude/workflows/qrspi-batch.js:2317-2318`

**Dependencies:** worker failure → `finResult` (no mutation) → gather re-read unchanged → resolver re-emits revise.
**Implicit contracts:** Counter progress requires a successful worker amend. There is NO orchestrator-side increment that fires on worker failure. (This is the structural gap the questions circle — see Q11.)

## Q9: If a revise amend changes file content but CI stays red (a partial/ineffective fix), is that counted as a consecutive-red attempt, and how is it distinguished from the "no change pushed" failure case?

**Answer:** Yes — a content-changing CI-failure revise IS counted: the worker prompt's CI-failure path sets the trailer to `<prior + 1>` (`qrspi-batch.js:2321` "This is the CI-FAILURE path (CI is RED): set the new value to <prior + 1>"). The increment happens because the worker touched a branch and ran the trailer-write `gt modify -m`. On the next run, if CI is still red, the gather re-reads the now-incremented trailer (N+1) and the resolver compares the higher count against the cap. The distinction from the "no change pushed" case is purely **whether the worker ran the trailer-write step at all** — there is no separate signal. A successful partial fix increments; a failed/no-change attempt does not. This means the cap currently counts *content-changing-but-ineffective* attempts but NOT *failed-no-change* attempts.

**Evidence:**

```javascript
   b. Compute the new trailer value PATH-DEPENDENTLY:
      ${ciFailing ? '- This is the CI-FAILURE path (CI is RED): set the new value to <prior + 1> ...'
                  : '- This is a NON-CI amend (no CI failure): overwrite the value to 0.'}
```

— `.claude/workflows/qrspi-batch.js:2320-2321`

**Dependencies:** worker (increment) → trailer → gather re-read → resolver cap compare.
**Implicit contracts:** "Consecutive red" is defined by the trailer + the read-side reset (any non-red gather run zeroes it, `qrspi_pr_state.py:305-308`). The increment is path-dependent in worker instructions, not in deterministic code — so the count only advances on a successful content amend.

## Q10: How is the terminal `wait` state currently represented in the resolver's output, and does the existing structure allow distinguishing "cap reached after failed attempts" from a normal cap-reached park?

**Answer:** `wait` is represented as a `decision` dict (`qrspi_resolve_state.py:185-197`) with `action:"wait"`, `phase`, a free-text `reason`, and `ciFailing` flag. The cap-reached park sets `ciFailing=True` and a distinct reason string "...still has failing CI after %d/%d consecutive auto-revise attempt(s); cap reached, parked for manual attention." (`qrspi_resolve_state.py:298-301`). **The structure does NOT distinguish "cap reached after failed (no-change) attempts" from "cap reached after content-changing attempts"** — there is a single cap-reached `wait` with `ciFailing=True`. There is no dedicated field/label for "gave up after repeated failed attempts" (AC4). The only differentiators today are `action` (string), `ciFailing` (bool), and the human-readable `reason`. The pending-CI wait (`qrspi_resolve_state.py:302-305`) and the review/thread waits (`qrspi_resolve_state.py:319-327`, `365-369`) are other `wait` variants distinguished only by `reason` text and (for pending) `ciFailing` absent.

**Evidence:**

```python
    def decision(action, **kw):
        out = {"action": action, "phase": kw.get("phase"), "nextPhase": ...,
               "discardPhases": ..., "commentTargets": ..., "changeRequested": ...,
               "ciFailing": kw.get("ciFailing", False), "reason": kw.get("reason", "")}
        return out
```

— `scripts/qrspi_resolve_state.py:185-197`

**Dependencies:** `decision` builder → consumed by `qrspi-batch.js` dispatch (`case 'wait'`, `qrspi-batch.js:2885`).
**Implicit contracts:** There is exactly one `wait` action value (`ACTIONS` enum, `qrspi_resolve_state.py:72`); all `wait` variants share a flat shape and are differentiated only by `reason`/`ciFailing`. No `gaveUp`/`capReason` field exists today.

## Q11: When the worker pushes no commit, how would an attempt counter advance without relying on the head-commit trailer write that only fires on a content amend — is there an alternate write point in the orchestrator that runs even on worker failure?

**Answer:** **NOT FOUND — there is no such alternate write point today.** Searched `qrspi-batch.js` for every `gt modify`/trailer-write site (grep `CI-Revise-Attempt|gt modify|trailer`): the only writes are (a) inside the `doRevise` CI-failure worker prompt (`qrspi-batch.js:2318-2323`), and (b) the `resetCiReviseTrailer` worker (`qrspi-batch.js:2421-2434`), which only writes 0. Both are LLM-worker `gt modify -m` invocations gated on a successful amend/apply. The post-worker handling in `doRevise` (`qrspi-batch.js:2329-2333`) and `finResult` (`qrspi-batch.js:2557-2563`) perform NO commit mutation. There is no deterministic orchestrator-side `gt modify -m` that fires on worker failure to advance `CI-Revise-Attempt`. **To advance the counter on a no-change failure, a new write point would have to be added** — e.g. an orchestrator-side trailer increment after a failed revise (analogous in mechanism to `resetCiReviseTrailer`, which already demonstrates a deterministic, worker-spawned, content-free `gt modify -m` to set a trailer value).

**Evidence:**

```javascript
async function resetCiReviseTrailer(t, r, d, answered) {
  ...
4. Otherwise rewrite the message with EXACTLY one `CI-Revise-Attempt: 0` line ...
   `gt modify --no-interactive -m "<the full rewritten message>"` ...
```

— `.claude/workflows/qrspi-batch.js:2410-2430` (the existing content-free trailer-write pattern, sets 0)

**Dependencies:** `resetCiReviseTrailer` is the closest existing analog; it is invoked from `doRevise:2277` and is best-effort (`qrspi-batch.js:2436`).
**Implicit contracts:** All trailer writes are routed through spawned workers running `gt modify -m`, never raw git, and the orchestrator never mutates a commit in deterministic JS. A new failed-attempt increment would have to follow the same worker-spawn pattern or introduce a deterministic helper script (cf. `qrspi_revise_amend.py`).

## Q12: What is the existing unit-test convention for the resolver and gather, and which test files cover the current CI-revise cap behavior from RUS-81?

**Answer:** Convention: stdlib-only `_test.py` siblings, each a standalone `python3 scripts/<name>_test.py` that exits 0/non-zero, aggregated by `scripts/run_tests.py` (`run_tests.py:1-48`, discovers every `*_test.py`, runs each as a subprocess). `scripts/qrspi_resolve_state_test.py` (521 lines) and `scripts/qrspi_pr_state_test.py` (757 lines) cover the resolver and gather. CI-revise cap coverage: in the resolver test, the block at `qrspi_resolve_state_test.py:343-437` ("CI-gated revise/wait (Slice 2)") exercises red/pending/green × frontier × cap boundaries; in the gather test, `qrspi_pr_state_test.py:103-189` covers `check_rollup_state`, the `ci_revise_attempt` trailer parser, the red-rollup pass-through, and the not-red→0 reset.

**Evidence:**

```python
# --- CI-gated revise/wait (Slice 2): red/pending/green/none × frontier/non-frontier × cap --
# T17a — red frontier (design) under cap -> revise + ciFailing=True.
case("CI red frontier (design) under cap -> revise + ciFailing",
     state(phases={"design": _phase(decision="REVIEW_REQUIRED", ci_state="red", ci_attempt=0)}),
     ... cap=3)
```

— `scripts/qrspi_resolve_state_test.py:343-352`

**Dependencies:** `run_tests.py` → discovers `*_test.py` → subprocess each. CI gate: `.github/workflows/tests.yml`.
**Implicit contracts:** Tests are pure (no network/disk); the resolver test feeds state dicts directly and the gather test feeds GraphQL-shaped nodes. New cap-counting behavior must add cases to these two files to pass `run_tests.py`.

## Q13: How do the existing CI-cap tests feed attempt-count state into the resolver, and what input fixtures represent a red frontier at/below/above the cap?

**Answer:** The resolver is pure, so the tests feed the attempt count directly as the `ciReviseAttempt` field on a synthetic phase dict — they do NOT exercise the trailer parser (that is the gather's job). Helpers `_phase(...)` (`qrspi_resolve_state_test.py:15-19`) and the impl-slice builder (`:32-35`) take a `ci_attempt=N` kwarg and emit `{"ciState": ci_state, "ciReviseAttempt": ci_attempt}`. `case(name, st, expect, cap=3)` (`:62-66`) threads the cap as the explicit `ci_revise_cap` argument to `resolve(st, ci_revise_cap=cap)` (`:494`). Fixtures: **under cap** = `ci_attempt=0` and `ci_attempt=2` with `cap=3` (`:349-350`, `:368-369`); **at cap** = `ci_attempt=3, cap=3` (`:356-357`); **above cap** = `ci_attempt=5, cap=3` (`:362-363`); plus cap-threading fixtures `ci_attempt=1` under `cap=1` (→wait) vs `cap=5` (→revise) (`:429-437`); and impl `max(...)` aggregation with mixed slice attempts (`:408-416`).

**Evidence:**

```python
def _phase(branch=True, pr=True, number=1, decision=None, threads=0, comment_targets=None,
           merged=False, ci_state="none", ci_attempt=0):
        ... "ciState": ci_state, "ciReviseAttempt": ci_attempt}
```

— `scripts/qrspi_resolve_state_test.py:14-19`

```python
def case(name, st, expect, cap=3):
    # `cap` is threaded into resolve(...) as the explicit ci_revise_cap argument
    CASES.append((name, st, expect, cap))
...
        got = resolve(st, ci_revise_cap=cap)
```

— `scripts/qrspi_resolve_state_test.py:62-66, 494`

**Dependencies:** `_phase`/`state`/`case` helpers → `resolve(..., ci_revise_cap=cap)`.
**Implicit contracts:** Because the resolver trusts the gathered effective count, the tests inject the *already-resolved* count — they never model "did the trailer get written." A test for failed-attempt counting (Q8/Q11) would belong in the gather/JS seam, not these pure resolver cases, OR would need a new resolver input field representing failed attempts.

## Q14: What does the batch run currently record/log as the per-ticket result for a `revise` vs a capped `wait`, and where would a "gave up after repeated failed attempts" distinction surface to the operator?

**Answer:** For BOTH actions the dispatcher first logs `  ${t.id}: decision=${a} — ${r.decision.reason}` (`qrspi-batch.js:2872`) — so the resolver's `reason` string (including the cap-reached text) is the operator-facing surface. For `revise`: `doRevise` runs and returns a result via `finResult` with `action:"revise"` and a summary, pushed to `results` (`qrspi-batch.js:2883`, `2891`); a worker failure yields `action:"revise"` + "revise finalize failed: ..." summary (`qrspi-batch.js:2560`). For a capped `wait`: the switch falls to the default/`wait` branch → `skip(t, r.decision, 'Skipped (wait): ' + r.decision.reason)` (`qrspi-batch.js:2885-2888`) → result `{action:"wait", summary:"Skipped (wait): <reason>"}`, then logs `  ${t.id}: skipped (wait)`. **A "gave up after repeated failed attempts" distinction would surface ONLY in the free-text `reason`/`summary` strings today** — there is no structured field. The cap-reached reason (`qrspi_resolve_state.py:298-301`) is the only place it is expressed, and it does not differentiate failed-no-change attempts from content-changing ones (per Q9/Q10).

**Evidence:**

```javascript
      case 'wait':         // not-yet-approved (or thread-only PR awaiting reviewer): nothing to do
      case 'entry_blocked':
      default:
        res = skip(t, r.decision, `Skipped (${a}): ${r.decision.reason}`)
        log(`  ${t.id}: skipped (${a})`)
```

— `.claude/workflows/qrspi-batch.js:2885-2889`

```javascript
function skip(t, decision, note) {
  return { ticketId: t.id, action: decision.action, summary: note }
}
```

— `.claude/workflows/qrspi-batch.js:635-637`

**Dependencies:** resolver `reason` → dispatch log (`:2872`) → `skip`/`finResult` → `results.push` → final per-ticket log (`:2898`).
**Implicit contracts:** Result records are `{ticketId, action, summary, [newStatus, prUrl]}`. Operator visibility is the `reason`/`summary` text only; any new "gave up" signal must be carried in `reason` or a new field added to both the resolver decision and the result record.

---

## Discovered Patterns

- **Pure functional core / imperative shell split.** All decision logic is pure Python in `qrspi_resolve_state.py` (no disk/network) and `qrspi_pr_state.py` (pure parsers over GraphQL dicts); the cap is *passed in* (`resolve(state, ci_revise_cap=3)`, `qrspi_resolve_state.py:173`). The orchestrator (`qrspi-batch.js`) is the harness-coupled imperative shell. Per CLAUDE.md, the JS is intentionally NOT unit-tested.
- **All commit mutation is delegated to spawned LLM workers running `gt`/`gt modify`, never raw git in JS.** Two distinct deterministic helpers exist for amends: `scripts/qrspi_revise_amend.py` (content amend, preserves message verbatim) and the worker-prompt `gt modify -m` (message-only trailer write). The orchestrator itself never mutates a commit.
- **Trailer-as-durable-state.** The `CI-Revise-Attempt` counter has no on-disk backing — it lives solely on the head commit and is observable via GitHub. The effective count is always re-derived at gather time with a not-red→0 reset, so a stale trailer on a now-green PR is inert.
- **Two-stage reset (read-side authoritative, writer-side hygienic).** The gather's not-red→0 is the correctness gate; the writer-side `resetCiReviseTrailer` is explicitly labeled "hygiene, not a correctness gate" (`qrspi-batch.js:2273-2275`).
- **Precedence-ordered resolver.** Decisions are evaluated in fixed slots: entry gate → reset → unified-feedback (2b) → CI-gated revise/wait (2c) → active-phase block. The CI slot is deliberately between feedback and active-phase (`qrspi_resolve_state.py:273-281`).
- **Worker honesty contract.** Every worker prompt is "HONESTY-BOUND: never fabricate a fix" and must return `ok:false` with a verbatim reason on failure (`qrspi-batch.js:2307`, `2326`, `2432`). Failures are recorded, not retried in-pass.

## Inconsistencies

- **The counter only advances on a *successful* content amend, but the cap is described as bounding "consecutive autonomous CI-failure revises" (`qrspi_resolve_state.py:176-177`).** A revise *attempt* that fails with no commit pushed is a real attempt but does NOT increment the trailer (Q2/Q8/Q11). So a perpetually-failing worker loops forever below the cap — the documented cap semantics ("N consecutive auto-revise attempts") do not match the implemented mechanism ("N successful content-changing amends that left CI red"). This is the gap the question set repeatedly probes; there is no code path that counts a failed-no-change attempt.
- **No structured signal distinguishes the two cap-reached / failure modes.** The `wait` decision shape (`qrspi_resolve_state.py:185-197`) has only `action`, `ciFailing`, and free-text `reason`. "Cap reached after content-changing-but-ineffective attempts" vs "stuck because the worker keeps failing with no change" are indistinguishable in structured output, and the AC4 "gave up after repeated failed attempts" distinction has nowhere to live except prose (Q10/Q14).
- **Comment vs code: `ci_revise_attempt_of` docstring says the gathered field is "already not-red->0 normalized at gather time ... so it is read directly here, never re-zeroed" (`qrspi_resolve_state.py:131-132`).** This is accurate for the read-side reset, but the *writer-side* reset (`resetCiReviseTrailer`) is a separate, best-effort mechanism whose failure the gather silently compensates for — a subtlety not reflected where the cap is compared. Two reset mechanisms exist for one logical reset, and only one (read-side) is load-bearing.
- **`ciFailingChecks` is emitted by the gather but the resolver never reads it** — it is re-emitted at the envelope top level for `doRevise` (`qrspi-batch.js:2238-2241`), not consumed by `resolve`. Correct by design, but the field lives in the gather's per-PR shape (`qrspi_pr_state.py:319`) alongside fields the resolver does read, which can mislead.
