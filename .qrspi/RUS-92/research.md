# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-19T00:00:00Z
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft

## Q1: How does the `CI-Revise-Attempt` trailer value flow from a PR's head-commit through the gather, into the resolver decision, and back out as a written trailer on the next amend?

**Answer:** The trailer is a head-commit message line `CI-Revise-Attempt: N`. The full round-trip is:

1. **Parse (gather):** `qrspi_pr_state.ci_revise_attempt(message)` parses the trailer off the head-commit message string with a `MULTILINE` regex; absent/malformed → `0`; last occurrence wins.
2. **Effective-count read-side reset (gather):** in `parse_pr_nodes`, the parsed value is forced to `0` whenever `ciState != "red"`. So the per-PR field `ciReviseAttempt` is the EFFECTIVE consecutive-red count, not the raw trailer.
3. **Resolver read:** `qrspi_resolve_state.ci_revise_attempt_of(phases, name)` reads `ciReviseAttempt` directly (never re-zeroes); for implementation aggregates per-slice via `max(...)`.
4. **Cap decision:** in `resolve()` step 2c, a red frontier with `attempt < ci_revise_cap` → `revise` (`ciFailing=True`); at/above cap → `wait` (`ciGaveUp=True`).
5. **Re-emit (one-shot orchestrator):** `qrspi_resolve.py` builds the envelope adding top-level `ciFailing`, `ciFailingChecks`, and `ciRedBranches` (the exact red branches to bump, derived by `red_branches_of`).
6. **Write-back (JS):** `doRevise` in `qrspi-batch.js` calls `bumpCiReviseTrailers` (CI path → writes `prior+1`) or `resetCiReviseTrailer` (non-CI path → writes `0`); the actual trailer rewrite is done by `scripts/qrspi_ci_revise_bump.py` (`bump_ci_revise_trailer`, same parse semantics as the gather — the shared serialization contract).

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

```python
ci_state = check_rollup_state(node)
...
if ci_state == "red":
    attempt = ci_revise_attempt(_head_commit(node).get("message"))
else:
    attempt = 0
```

— `scripts/qrspi_pr_state.py:303-308` (read-side reset)

**Dependencies:** `qrspi_pr_state.ci_revise_attempt` (parse) → `parse_pr_nodes` (effective field) → `qrspi_resolve_state.ci_revise_attempt_of` / `resolve` (cap) → `qrspi_resolve.red_branches_of` + envelope (re-emit) → `qrspi-batch.js doRevise` → `qrspi_ci_revise_bump.py` (write). The trailer is the shared serialization contract between writer (`qrspi_ci_revise_bump.py`) and reader (`qrspi_pr_state.ci_revise_attempt`).

**Implicit contracts:** Reader and writer MUST share parse semantics (absent⇒0, last-occurrence-wins, exactly one trailer). The resolver consumes ONLY the already-normalized `ciReviseAttempt` field, never the raw message; it must not re-zero. The cap comparison is `attempt < cap` (strict): `attempt == cap` is already parked.

## Q2: What inputs does `bumpCiReviseTrailers`/`resetCiReviseTrailer` read to decide bump-on-CI-path versus reset-on-every-non-CI-amend, and which of those inputs are already available to `qrspi_resolve_state.py` versus computed only inside `qrspi-batch.js`?

**Answer:** The bump-vs-reset choice is made in `doRevise`, not inside the helpers. The deciding inputs:

- `ciFailing` = `!!(r.ciFailing || (d && d.ciFailing))` — read from the resolver envelope top level (`r.ciFailing`) or the decision (`d.ciFailing`).
- `changeRequested` = `!!(d && d.changeRequested)` — from the decision.

Path selection (`doRevise`):
- `if (ciFailing)` → `bumpCiReviseTrailers(t, r, d)` (writes prior+1 on each `r.ciRedBranches`).
- `else if (changeRequested)` → `resetCiReviseTrailer(t, r, d, answered)` (writes 0, unconditional/idempotent).
- Comment-only path (`!changeRequested && !ciFailing`) also calls `resetCiReviseTrailer` but ONLY `if (answered.some(a => a.applied))` (i.e. an amend actually happened).

`bumpCiReviseTrailers` reads `r.ciRedBranches` (the ascending red-branch list re-emitted by the resolver). `resetCiReviseTrailer` reads `d.phase` (to form the branch hint) and `answered` (only as a hint; the worker rewrites whatever branch(es) it amended).

**What is already available to the resolver vs JS-only:** `ciFailing`, `changeRequested`, and `ciRedBranches` are ALL produced on the resolver side — `ciFailing`/`changeRequested` are decision fields and `ciRedBranches` is re-emitted by `qrspi_resolve.red_branches_of`. The JS does NOT recompute which branches are red (deliberately — Option A' removes that LLM non-determinism). The JS-only inputs are `answered`/`answered.some(a=>a.applied)` (the per-comment apply result, from `respondToComments`) — this is the only signal that lives purely in JS.

**Evidence:**

```javascript
if (ciFailing) {
    const bump = await bumpCiReviseTrailers(t, r, d)
    if (out && !bump.ok) { ... out.ciReviseBumpFailed = true ... }
} else if (changeRequested) {
    await resetCiReviseTrailer(t, r, d, answered)
}
```

— `.claude/workflows/qrspi-batch.js:1019-1038`

```javascript
const branches = Array.isArray(r.ciRedBranches) ? r.ciRedBranches : []
```

— `.claude/workflows/qrspi-batch.js:1184` (bumpCiReviseTrailers input)

**Dependencies:** `doRevise` ← `r.ciFailing`/`r.ciRedBranches` (envelope, from `qrspi_resolve.py`) ← `decision` (from `qrspi_resolve_state.resolve`). Both helpers spawn LLM workers that run `qrspi_ci_revise_bump.py` (bump) or a bare `gt modify -m` (reset).

**Implicit contracts:** Exactly one writer per path (bump XOR reset). The bump fires UNCONDITIONALLY when `ciFailing` (even if the content worker reported failure), so an unfixable red PR still marches to the cap — this is the AC6 guarantee. The comment-only reset is gated on `applied` because pure ANSWER/DECLINE touches no commit.

## Q3: What is the current input/output contract of `qrspi_resolve_state.py` (the verdict object it returns), and what fields would need to be added to carry the CI-Revise counter verdict to the JS caller?

**Answer:** `resolve(state, ci_revise_cap=3)` is pure (no I/O). Input: the gathered state dict (`assigned`, `linearStatus`, `blockedOpen`, `blockedBy`, `phases.{design,plan,implementation}` with per-PR fields including `ciState`/`ciReviseAttempt`/`commentTargets`), plus the cap passed in by the caller. Output: a fixed-key decision dict built by the inner `decision(...)` factory:

```python
out = {
    "action": action,           # one of ACTIONS
    "phase": kw.get("phase"),
    "nextPhase": kw.get("nextPhase"),
    "resetToPhase": kw.get("resetToPhase"),
    "discardPhases": kw.get("discardPhases", []),
    "commentTargets": kw.get("commentTargets", []),
    "changeRequested": kw.get("changeRequested", False),
    "ciFailing": kw.get("ciFailing", False),
    "ciGaveUp": kw.get("ciGaveUp", False),
    "reason": kw.get("reason", ""),
}
```

— `scripts/qrspi_resolve_state.py:185-198`

**The CI-Revise counter verdict is ALREADY carried** — there is no missing field for the cap decision itself: `ciFailing` (red under cap → revise) and `ciGaveUp` (red at/above cap → wait) already encode the verdict, and the human-readable reason already names the attempt count and cap (`"attempt %d/%d"`). What is NOT on the decision dict is the per-branch red list (`ciRedBranches`) and the failing-check details (`ciFailingChecks`) — those are deliberately re-emitted at the ENVELOPE top level by `qrspi_resolve.py` (`red_branches_of`, `ci_failing_checks_of`), because "the `decision` dict's key set is fixed and the gather attaches per-slice `ciState` only inside `phases`" (`scripts/qrspi_resolve.py:237-244`). If RUS-92 wants the resolver itself (not the one-shot wrapper) to surface a richer counter verdict, the candidates would be an explicit `ciReviseAttempt`/`ciReviseCap` echo on the decision dict — currently they appear only inside `reason`.

**Dependencies:** Callers: `qrspi_resolve.py` (line 560, `resolve(state, ci_revise_cap=ci_revise_cap)`) and the resolver's own `main()` (defaults cap to 3). The `decision()` factory is the single construction point — any new field must be added there to keep the key set uniform across all 8 actions.

**Implicit contracts:** The decision dict has a FIXED key set (every action returns all keys, defaulted). The resolver is PURE — it does NO disk read; the cap is passed in. Default `ci_revise_cap=3` keeps it additive for callers that have not threaded the cap.

## Q4: Which exact strings do the five design-critic agent files declare for their spawn path, and what is the precise current wording versus what the impl-review file says?

**Answer:** Exactly FIVE files contain the literal string `Spawned by runCriticPanelLoop in qrspi-batch.js`:

1. `.claude/agents/qrspi-design-critic-completeness.md:3`
2. `.claude/agents/qrspi-design-critic-edge-alignment.md:3`
3. `.claude/agents/qrspi-design-critic-internal-consistency.md:3`
4. `.claude/agents/qrspi-design-critic-simplicity.md:3`
5. `.claude/agents/qrspi-design-critic-design-review.md:3` — variant: `Spawned by runCriticPanelLoop in qrspi-batch.js (opt-in, default-OFF).`

The four (completeness/edge-alignment/internal-consistency/simplicity) say plainly `Spawned by runCriticPanelLoop in qrspi-batch.js.`; design-review adds the `(opt-in, default-OFF)` qualifier.

By contrast, `qrspi-impl-critic-impl-review.md:3` says: `Spawned by the /review-implementation command (advisory, propose-only).` — it points at the `/review-*` command, NOT `runCriticPanelLoop`.

**Evidence (design-review, the node-validity lens):**

```
description: Internal QRSPI workflow agent — the adversarial NODE-VALIDITY lens of the
design-phase critic panel (DESIGN-REVIEW). ... Spawned by runCriticPanelLoop in
qrspi-batch.js (opt-in, default-OFF). Not for general code review.
```

— `.claude/agents/qrspi-design-critic-design-review.md:3`

```
description: ... the adversarial NODE-VALIDITY lens of the implementation-phase critic
panel (IMPL-REVIEW). ... Spawned by the /review-implementation command (advisory,
propose-only). Not for general code review.
```

— `.claude/agents/qrspi-impl-critic-impl-review.md:3`

**Inconsistency (significant for AC):** `runCriticPanelLoop` is referenced in these five design-critic descriptions, but it NO LONGER EXISTS as a live spawn path in `qrspi-batch.js`. The batch runs NO critics — `runPhase`'s comment states: "the autonomous batch runs no critics or node-checks (the design panel, N-select, coherence pass, and research citation check were all removed; the on-demand /review-* family is the surviving review path)" (`qrspi-batch.js:509-511`). A grep for `runCriticPanelLoop` in `qrspi-batch.js` returns ONLY these agent-file references (no definition/call). The plan-critic and impl-critic peers already say "Spawned by the /review-{plan,implementation} command". So the five design-critic files carry STALE pivot residue: they should match the plan/impl peers and point at `/review-design`.

**Dependencies:** These are agent description front-matter strings (triggering/orientation text), read by the harness/skill-router, not executed. The live consumers are the `/review-design|plan|implementation` SKILL wrappers → `qrspi-review.js` (the deterministic review engine, per git log).

**Implicit contracts:** Agent descriptions are documentation/triggering surface; a stale spawn reference does not break execution but misdescribes the live wiring (this is the "pivot residue" the ticket targets).

## Q5: How is the CI-Revise-Attempt counter state currently derived inside `doRevise` — read-side reset vs writer-side reset vs bump path?

**Answer:** `doRevise` itself does NOT derive the read-side reset — that is done at gather time. The three behaviors:

- **Read-side reset (gather, NOT doRevise):** `parse_pr_nodes` sets `attempt = 0` whenever `ci_state != "red"` (`qrspi_pr_state.py:303-308`). So the EFFECTIVE count the resolver sees is already 0 on any non-red PR.
- **Writer-side reset (doRevise → `resetCiReviseTrailer`):** every non-CI amend overwrites the committed trailer to `CI-Revise-Attempt: 0`. Triggered on the green-CI change-request path (unconditional, idempotent) and on the comment-only path only when a comment was actually applied (`answered.some(a => a.applied)`).
- **Bump path (doRevise → `bumpCiReviseTrailers` → `qrspi_ci_revise_bump.py`):** on the CI-failure path, writes `prior+1` on every still-red branch in `r.ciRedBranches`, unconditionally after the content worker returns.

The writer-side reset is described as durability/observability hygiene on the committed head, NOT a correctness gate — the gather's read-side reset already forces the effective count to 0 while CI is not red (`qrspi-batch.js:959-962`, `1128-1129`, `1147`).

**Evidence:**

```javascript
// RUS-81 writer-side reset: a comment APPLY amends ... preserves the message verbatim — so a
// stale CI-Revise-Attempt trailer ... would survive this NON-CI amend. ... EVERY non-CI amend
// overwrites the trailer to 0. Only needed when a comment was actually applied ...
if (answered.some(a => a.applied)) {
  await resetCiReviseTrailer(t, r, d, answered)
}
```

— `.claude/workflows/qrspi-batch.js:956-965`

**Dependencies:** `doRevise` ← gather's `ciReviseAttempt` (read-side reset) and `r.ciRedBranches` (bump targets). `bumpCiReviseTrailers` delegates the actual rewrite to `qrspi_ci_revise_bump.py`; `resetCiReviseTrailer` uses a bare `gt modify -m` LLM worker.

**Implicit contracts:** Two resets coexist by design — read-side (effective count, correctness) and writer-side (committed head, hygiene). The bump must be deterministic + unconditional so the cap can fire even when the content worker keeps failing.

## Q6: Where is the cap value (`ciReviseCap`) read and how is the at-cap red → `wait` switch computed, and is that logic in the resolver already or still in JS?

**Answer:** The cap READ is in `scripts/qrspi_resolve.py` (the one-shot orchestrator), NOT in the resolver and NOT in JS:

- `load_ci_revise_cap(repo_root)` reads `.qrspi/config.json` via `qrspi_config.read_config` (a SINGLE flat top-level key — no dot-path) and coerces with `coerce_cap`.
- `coerce_cap(value)` returns the value if a positive int, else the default `3` (rejects bool, non-int, non-positive). Constant `CI_REVISE_CAP_DEFAULT = 3`.
- `qrspi_resolve.py:559-560` reads the cap and passes it: `decision = resolve(state, ci_revise_cap=ci_revise_cap)`.

The at-cap switch is ENTIRELY in the resolver (`qrspi_resolve_state.resolve`, step 2c), already pure logic — NOT in JS:

```python
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

**Evidence (cap read):**

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

**Dependencies:** `qrspi_resolve.load_ci_revise_cap` → `qrspi_config.read_config` → `.qrspi/config.json`. The resolver receives the cap as a parameter (default 3) and does NO disk read. JS does NOT read the cap at all — it consumes `ciFailing`/`ciGaveUp` off the envelope.

**Implicit contracts:** The cap is config-driven, fail-closed to 3 on any invalid/missing value. The at-cap decision lives in the tested pure resolver — so RUS-92 cap/transition tests belong in `qrspi_resolve_state_test.py` (cap is already a `resolve(...)` parameter and the test harness already threads `cap=`). The comparison is strict `attempt < cap` (at-cap parks).

## Q7: What does the trailer-write code do when a head commit has no `CI-Revise-Attempt` trailer at all, or a malformed/non-integer value?

**Answer:** Defaulting is centralized in the PURE parse functions, shared by reader and writer:

- **Parse/read (`ci_revise_attempt`):** no trailer → `0`; non-integer / malformed → `0` (regex only matches `\d+`, and the `int()` is wrapped in try/except). Multiple occurrences → last wins.
- **Bump write (`qrspi_ci_revise_bump.bump_ci_revise_trailer`):** uses the SAME parse semantics — "absent ⇒ prior = 0, last-occurrence wins; the result carries EXACTLY one `CI-Revise-Attempt: <prior+1>` trailer with the subject and every other trailer byte-preserved" (`qrspi_ci_revise_bump.py:28-32`). So an absent trailer bumps to `1`.
- **Reset write (`resetCiReviseTrailer` worker prompt):** if there is NO `CI-Revise-Attempt:` line, skip — "do NOT add one; absent already means 0"; if present and already 0, no-op; otherwise rewrite to exactly one `CI-Revise-Attempt: 0`.

**Evidence:**

```javascript
2. If there is NO `CI-Revise-Attempt:` line, there is nothing to reset — skip this branch
   (do NOT add one; absent already means 0).
3. If a `CI-Revise-Attempt: N` line is present and N is already 0, skip (no-op).
4. Otherwise rewrite the message with EXACTLY one `CI-Revise-Attempt: 0` line ...
```

— `.claude/workflows/qrspi-batch.js:1139-1141`

(parse defaulting evidence at `scripts/qrspi_pr_state.py:124-130`, Q1)

**Dependencies:** Reader (`qrspi_pr_state.ci_revise_attempt`) and writer (`qrspi_ci_revise_bump.bump_ci_revise_trailer`) explicitly share the same defaulting contract — they are coupled by the trailer serialization format.

**Implicit contracts (MUST preserve):** absent ⇒ 0; malformed ⇒ 0; last-occurrence wins; exactly one trailer after a write; subject + all other trailers byte-preserved; reset never ADDS a trailer to a commit that lacks one (absent already means 0). Any RUS-92 test of bump/reset must respect these.

## Q8: How does the counter behave for the implementation phase where CI is aggregated across the slice stack, and does the per-slice aggregation interact with the single head-commit trailer?

**Answer:** CI state and the attempt counter are aggregated differently:

- **CI state aggregation (`ci_state`):** for implementation, any slice `red` → `red`; else any `pending` → `pending`; else any `green` → `green`; else `none` (`qrspi_resolve_state.py:117-126`).
- **Attempt aggregation (`ci_revise_attempt_of`):** for implementation, `max(...)` of the per-slice `ciReviseAttempt` values — "the highest attempt governs the cap" (`qrspi_resolve_state.py:135-138`). So one slice at cap parks the WHOLE stack as `wait` even if another red slice is under cap (test T at `qrspi_resolve_state_test.py:408`).

There is NOT a single head-commit trailer for the stack — EACH slice branch has its OWN head-commit trailer. The gather parses each slice's trailer (with its own red-state read-side reset), the resolver aggregates via `max`. On write-back, `red_branches_of` returns EACH red slice as `"<ticket>/slice-<n>"` ascending, and `bumpCiReviseTrailers` bumps EACH such slice's trailer individually (per-branch), lowest-first.

**Evidence:**

```python
def ci_revise_attempt_of(phases, name):
    if name == "implementation":
        attempts = [int(s.get("ciReviseAttempt", 0) or 0) for s in _impl_slices(phases)]
        return max(attempts) if attempts else 0
    return int(phases.get(name, {}).get("ciReviseAttempt", 0) or 0)
```

— `scripts/qrspi_resolve_state.py:129-138`

**Dependencies:** Per-slice `ciState`/`ciReviseAttempt` attached by the gather's slice loop (`qrspi_pr_state.py:598-603`) → `ci_state`/`ci_revise_attempt_of` aggregation (resolver) → `red_branches_of` per-slice expansion (`qrspi_resolve.py:236-260`) → `bumpCiReviseTrailers` per-branch loop (`qrspi-batch.js:1190-1207`).

**Implicit contracts:** The stack is "reviewed as a whole" — any-red aggregation for state, max for the cap. The trailer is per-branch, not stack-level; the bump operates per red slice, ascending (changes restack upward). An incomplete stack (later slices not yet built, contributing `ciState="none"`) still aggregates to `red` if any built slice is red, and is revised BEFORE `advance` builds the next slice (`qrspi_resolve_state.py:284-287`).

## Q9: Which files are written by more than one slice (notably `qrspi-batch.js` touched by slices 1 and 2), and what are the exact line ranges of the dead-path comments (~525–561, ~810–833)?

**Answer:** This question's premise is about SLICING THE RUS-92 IMPLEMENTATION (which slices touch which files), which is a forward-looking concern; the codebase facts I can establish:

The single most cross-cut file in the CI-revise/critic/eval surface is `.claude/workflows/qrspi-batch.js` (1682 lines total). The CI-revise logic lives in `doRevise` (918-1045), `resetCiReviseTrailer` (1131-1150), and `bumpCiReviseTrailers` (1183-1209); the result-recording/log surface is in the dispatch switch (1644-1662) and per-ticket log (1670); the no-critics statement is at `runPhase` (509-511).

**The cited line ranges (~525–561, ~810–833) do NOT correspond to dead-path comments.** I read both:
- Lines 525-561 are LIVE code: `runPhase`'s `persistArtifact` call + return (522-531) and the start of `resolveTicket`'s Linear-fetch prompt (537-561). Not dead-path comments.
- Lines 810-833 are LIVE code: the slice-implementation failure branch + the slice-commit worker prompt (809-833). Not dead-path comments.

The actual "removed/no-longer/dead" residue comments in `qrspi-batch.js` are at: `48`, `60`, `137`, `168`, `325`, `509-511` (the removed critic panel statement), `900`, `974`, `1016`, `1033` ("the deleted worker step-6"), `1062`, `1065`, `1169` ("Replaces the deleted worker step-6 CI +1"), `1212` ("Replaces the old unsafe..."). **The line citations in the question appear stale** — likely drifted from an earlier file version.

**Evidence (the removed-critics statement, the closest thing to a "dead path" comment in the cited region):**

```javascript
// The phase persists ungated — the autonomous batch runs no critics or
// node-checks (the design panel, N-select, coherence pass, and research citation check
// were all removed; the on-demand /review-* family is the surviving review path).
```

— `.claude/workflows/qrspi-batch.js:509-511`

**Dependencies:** N/A (slicing/collision concern). The whole file is harness-coupled and NOT unit-testable in isolation (top-level `return`, injected globals — `.claude/CLAUDE.md` Codebase conventions, the "JS coverage of `qrspi-batch.js` is deferred" note).

**Implicit contracts:** Any RUS-92 plan that asserts specific line ranges in `qrspi-batch.js` MUST re-derive them against the live file — the questions' `~525-561 / ~810-833` citations are stale. Re-grep `removed|no longer|deleted worker|the old` to locate the true residue comments before editing.

## Q10: What is the existing unit-test structure and assertion style for `qrspi_resolve_state.py`?

**Answer:** `scripts/qrspi_resolve_state_test.py` is stdlib-only, assert-based (no pytest), matching repo convention; run with `python3 scripts/qrspi_resolve_state_test.py`, exits 0 all-pass / 1 on first failure. Structure:

- **Builders:** `_phase(...)`, `_impl(slices, ...)`, `_slice(n, ...)`, `_ct(cid)` (CommentTarget), `state(...)` assemble the gathered-state dict. `_phase`/`_slice` already accept `ci_state=` and `ci_attempt=` kwargs (CI fields are first-class in the fixtures).
- **Registration:** `case(name, st, expect, cap=3)` appends `(name, st, expect, cap)` to a module-level `CASES` list. `cap` is threaded into `resolve(...)` — default 3, overridden by CI-cap cases.
- **Assertion:** `run()` iterates `CASES`, calls `resolve(st, ci_revise_cap=cap)`, and for each `key, want` in `expect` checks `got.get(key) != want`. Special key `_reasonContains` asserts each needle is a substring of the reason (via `contains` helper).
- **Existing CI-cap coverage:** an entire section (`qrspi_resolve_state_test.py:343-474`) already exercises red/pending/green × frontier/non-frontier × cap boundaries, `ciFailing`, `ciGaveUp`, per-slice `max` aggregation, and cap-threading (cap=1 / cap=5).

**Evidence:**

```python
def case(name, st, expect, cap=3):
    CASES.append((name, st, expect, cap))
...
for name, st, expect, cap in CASES:
    got = resolve(st, ci_revise_cap=cap)
    ...
    if key == "_reasonContains":
        missing = [n for n in want if not contains(got.get("reason", ""), n)]
    ...
    if got.get(key) != want:
        print("FAIL: ...")
```

— `scripts/qrspi_resolve_state_test.py:62-66, 550-569`

**Dependencies:** Imports `from qrspi_resolve_state import resolve`. Discovered + run by `scripts/run_tests.py` (globs `scripts/*_test.py`, runs each as a subprocess, non-zero if any fails). The aggregating runner is the CI gate (`.github/workflows/tests.yml`).

**Implicit contracts:** New bump/reset/cap-transition tests should be added as `case(...)` entries using the existing `_phase`/`_slice` builders with `ci_state=`/`ci_attempt=` and a `cap=` override, asserting `action`, `ciFailing`, `ciGaveUp`, and `_reasonContains`. Tests must stay stdlib-only and pass under `python3 scripts/run_tests.py resolve`. NOTE: the bump/reset WRITE logic lives in `qrspi_ci_revise_bump.py` (has its own `_test.py` sibling) and the JS `doRevise` (not unit-testable) — only the cap DECISION is testable in `qrspi_resolve_state_test.py`.

## Q11: Which exact files contain the six "non-functional placeholder" eval references and the stale line citations, and what is the current wording at each location?

**Answer:** Six locations:

1. `.claude/CLAUDE.md:187` — `- The `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** — verify` (continues: "pure logic with the unit tests and orchestration changes with manual end-to-end runs").
2. `docs/qrspi-orientation.md:76` — `> The `evals/` harness is a **non-functional placeholder**. Verification of QRSPI itself` ...
3. `docs/eval-system.md:7, 97, 101` — describes `scripts/run_eval.py` as executing test cases; line 97 cites `run_eval.py:117-137` ("Stub — no actual agent invocation"); line 101 cites `revise.py:26-44` ("placeholder edits"). These embedded LINE citations are the stale-citation risk AC2 targets.
4. `docs/qrspi_quick_reference.md:208` — `evals/                              NON-FUNCTIONAL placeholder. Verification = unit` ...
5. `docs/qrspi_practical_application.md:185` — "... the unit tests; the `evals/` harness is a non-functional placeholder, so verification is unit ..."
6. `scripts/eval_all.py:11` — in the module docstring: "the underlying single-agent path (``run_eval.py`` + ``grade.py``) is a non-functional placeholder whose ``execute_single`` returns empty output (see CLAUDE.md / RUS-41 OQ4), so real scores against the stubbed harness are uniformly ~0."

**Evidence:**

```
This is a *plumbing* driver, not a scorer: the underlying single-agent path
(``run_eval.py`` + ``grade.py``) is a non-functional placeholder whose
``execute_single`` returns empty output (see CLAUDE.md / RUS-41 OQ4), so real
scores against the stubbed harness are uniformly ~0.
```

— `scripts/eval_all.py:10-13`

```
| Agent execution runtime | Stub | `run_eval.py:117-137` — no actual agent invocation |
| Meta-agent revision | Stub | `revise.py:26-44` — placeholder edits |
```

— `docs/eval-system.md:97, 101`

**Inconsistency / verification flag for AC2:** The embedded line citations (`run_eval.py:117-137`, `revise.py:26-44`) in `docs/eval-system.md` are hard-coded to a file version and are the kind of stale-line citation the ticket flags. Whether `evals/scripts/run_eval.py`'s `execute_single` still sits at 117-137 (and whether `revise.py` lines are accurate) must be re-verified against the live files before AC2 "corrects" them — I have NOT re-confirmed those line numbers against the current `evals/` tree.

**Dependencies:** These are documentation/docstring strings (not executed). The MEMORY/CLAUDE single-source-of-truth for the placeholder claim is `.claude/CLAUDE.md:185-187`.

**Implicit contracts:** The placeholder status is documented consistently across all six; a correction must keep them consistent. Project MEMORY records "Eval harness is a placeholder" — any wording change should not contradict that memory.

## Q12: What are the five `qrspi_*` guide-pack docs and the meta-index doc, and where is the PR-gated lifecycle narrative currently duplicated?

**Answer:** The `docs/qrspi_*` (underscore) guide-pack files are FIVE:

1. `docs/qrspi_claude_code_guide.md`
2. `docs/qrspi_complete_guide.md`
3. `docs/qrspi_practical_application.md`
4. `docs/qrspi_quick_reference.md`
5. `docs/qrspi_working_example.md`

The meta-index / orientation doc is `docs/qrspi-orientation.md` (hyphenated). The canonical design narrative is `docs/qrspi-pr-gated-lifecycle-design.md` (`# QRSPI PR-Gated Lifecycle — Design`, "all decisions locked (12)").

**PR-gated lifecycle narrative duplication** appears in at least three live places (besides the canonical design doc):

1. `.claude/CLAUDE.md` "### Lifecycle — PR-gated" section — the full `Selected → design PR → plan PR → slice PRs → land` ASCII flow, branch naming, advance/reset/revise/CI rules (the longest copy).
2. `.claude/skills/qrspi-work/SKILL.md:9, 28-29` — `# QRSPI Work Orchestrator (PR-gated)` + "A single Graphite stack per ticket, built bottom-up and **held open** until the whole feature is approved, then landed bottom-up:" — restates the same stack/lifecycle model and the `Selected` entry gate (line 15), the `Design Review` projection (lines 197-198), and reset (line 432).
3. The batch comments in `qrspi-batch.js` (e.g. `48`, the lifecycle/revise/CI prose around `887-917`, `1016-1043`) — narrative descriptions of the same advance/revise/CI/cap rules.

All four (CLAUDE.md, qrspi-work SKILL, batch comments, and the design doc) independently narrate the same `Selected → Design Review → Plan Review → Code Review → Done` projection and the bottom-up stack model.

**Evidence:**

```
A single Graphite stack per ticket, built bottom-up and **held open** until the whole
feature is approved, then landed bottom-up:
```

— `.claude/skills/qrspi-work/SKILL.md:28-29`

**Dependencies:** `docs/qrspi-pr-gated-lifecycle-design.md` is referenced as the source of truth by `.claude/CLAUDE.md` ("See `docs/qrspi-pr-gated-lifecycle-design.md` for the full design"). The guide-pack docs and qrspi-work SKILL are downstream restatements.

**Implicit contracts:** The design doc is the canonical narrative; the other copies are projections/summaries. Any de-duplication must preserve the entry-gate and projection-status invariants (`Selected` / `Design Review` / `Plan Review` / `Code Review` / `Done`) since the resolver and workers key on them.

## Q13: How is the counter's state surfaced to a human when the cap is reached and the resolver switches red → `wait`?

**Answer:** Two signals flow to the human:

1. **Resolver reason + `ciGaveUp`:** at cap, `resolve` returns `decision("wait", phase=frontier, ciFailing=True, ciGaveUp=True, reason="%s frontier PR still has failing CI after %d/%d consecutive auto-revise attempt(s); CI-revise cap reached — gave up auto-revising, parked for manual diagnosis.")` (`qrspi_resolve_state.py:299-303`). The attempt count and cap are embedded in the reason string.

2. **JS surfacing:** the `wait`/`entry_blocked` switch arm calls `skip(t, r.decision, ...)`, and `skip` carries `ciGaveUp` onto the result record (`qrspi-batch.js:472`). The per-ticket log appends `' — CI-revise cap reached, auto-revise GAVE UP; parked for manual diagnosis'` when `r.decision.ciGaveUp` (`qrspi-batch.js:1659-1661`), and the run-summary log line appends `' (CI-revise cap reached — auto-revise gave up, manual diagnosis needed)'` when `res.ciGaveUp` (`qrspi-batch.js:1670`). Additionally, a failed bump surfaces `res.ciReviseBumpFailed` with `' (CI-Revise-Attempt counter failed to advance)'` (`qrspi-batch.js:1029-1030, 1670`).

**Evidence:**

```python
return decision("wait", phase=frontier, ciFailing=True, ciGaveUp=True,
                reason="%s frontier PR still has failing CI after %d/%d "
                       "consecutive auto-revise attempt(s); CI-revise cap reached "
                       "— gave up auto-revising, parked for manual diagnosis."
                       % (frontier, attempt, ci_revise_cap))
```

— `scripts/qrspi_resolve_state.py:299-303`

```javascript
log(`  ${t.id}: skipped (${a})${r.decision.ciGaveUp ? ' — CI-revise cap reached, auto-revise GAVE UP; parked for manual diagnosis' : ''}`)
```

— `.claude/workflows/qrspi-batch.js:1661`

**Dependencies:** Resolver `ciGaveUp`/reason → envelope → `skip()` (`qrspi-batch.js:466-474`) → result record + per-ticket log (1659-1661) + run-summary log (1670). The result record is what an operator/log reader sees; there is NO Linear write for the give-up (status stays in the active review state).

**Implicit contracts:** A moved-to-resolver verdict MUST preserve `ciGaveUp` (and the attempt/cap in the reason) so the JS log surfacing stays informative — the resolver already owns this signal; `skip()` passes it through verbatim, and the decision dict's `ciGaveUp` key is the carry channel. The signal is log-only (no Linear projection) by design.

---

## Discovered Patterns

- **Pure functional core / imperative shell split:** All decision and parse logic lives in pure, stdlib-only, unit-tested Python (`qrspi_resolve_state.py`, `qrspi_pr_state.py`, `qrspi_config.py`, `qrspi_ci_revise_bump.py`); the harness-coupled `qrspi-batch.js` is the imperative shell (explicitly NOT unit-testable — top-level `return`, injected globals). RUS-92 test work belongs on the Python side.
- **Self-locating scripts:** `qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_config.py`, `qrspi_ci_revise_bump.py` all derive `REPO_ROOT` from `__file__` (or `qrspi_paths.resolve_repo_root()`), so workers type one invocation and never mangle the `qrspi` path token.
- **Shared serialization contract:** the `CI-Revise-Attempt` trailer is parsed identically by reader (`qrspi_pr_state.ci_revise_attempt`) and writer (`qrspi_ci_revise_bump.bump_ci_revise_trailer`); both default absent⇒0 and last-occurrence-wins.
- **Two-reset design for the counter:** read-side (gather, effective-count correctness) + writer-side (committed-head hygiene). The read-side reset is authoritative for the cap; the writer-side is cleanliness.
- **Fixed-key decision dict:** the resolver's `decision()` factory returns all keys for every action — additive fields must be added there to stay uniform.
- **Orchestrator-owned, unconditional counter writes:** the bump fires regardless of worker success (so the cap can fire on a genuinely-stuck PR); exactly one writer per path (bump XOR reset).
- **Agent descriptions encode spawn provenance:** every critic agent's front matter names its spawn path — these are the pivot-residue strings RUS-92 targets.

## Inconsistencies

- **Stale `runCriticPanelLoop` references (Q4):** the five design-critic files say "Spawned by runCriticPanelLoop in qrspi-batch.js", but `qrspi-batch.js` has NO `runCriticPanelLoop` definition or call (grep returns only these agent-file mentions), and `runPhase:509-511` states the batch runs no critics. The plan-critic and impl-critic peers already point at the `/review-*` commands — the design-critic five are out of sync.
- **Stale line citations in the questions (Q9):** the cited dead-path comment ranges `~525-561` and `~810-833` in `qrspi-batch.js` are LIVE code in the current file, not dead-path comments. The true residue comments are elsewhere (48, 168, 509-511, 1033, 1169, 1212, ...). Any plan asserting line ranges must re-derive against the live 1682-line file.
- **Stale line citations in `docs/eval-system.md` (Q11):** the embedded `run_eval.py:117-137` and `revise.py:26-44` citations are version-pinned; their accuracy against the current `evals/` tree is UNVERIFIED here and is precisely what AC2 must re-check.
- **Lifecycle narrative duplicated 4× (Q12):** the same PR-gated lifecycle/projection narrative is independently restated in `.claude/CLAUDE.md`, `.claude/skills/qrspi-work/SKILL.md`, the `qrspi-batch.js` comments, and the canonical `docs/qrspi-pr-gated-lifecycle-design.md` — a drift hazard the doc-bloat AC targets.
- **CI-Revise cap decision is fully tested but the WRITE side is split across testability boundaries:** the cap DECISION is unit-tested in `qrspi_resolve_state_test.py`; the bump WRITE is tested in `qrspi_ci_revise_bump_test.py`; but the doRevise bump/reset ORCHESTRATION (which helper fires when) lives in the non-unit-testable `qrspi-batch.js`. The "untested CI-revise counter" framing in the ticket title may refer to this orchestration seam, not the pure cap logic (which IS covered).
