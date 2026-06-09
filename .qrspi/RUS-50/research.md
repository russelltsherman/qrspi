# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-08T00:00:00Z
**Generated:** 2026-06-08T00:00:00Z
**Status:** draft

## Q1: How does the resolve worker's `get_issue` call currently extract `assigned` and `linearStatus`, and where in that path would a `blockedBy`-derived flag be assembled before invocation of `qrspi_resolve.py`?

**Answer:** The RESOLVE worker is a natural-language agent prompt in `resolveTicket(t)`. Step 1 instructs the worker to call `mcp__linear__get_issue` for the ticket identifier and read two facts: the status name and whether the issue is assigned (`assignee non-null`). There is NO structured extraction in JS — the worker reads the MCP payload itself, then in step 3 substitutes the status into `--linear-status "<status>"` and conditionally appends `--assigned`. A `blockedBy`-derived flag would be assembled in this same prompt: the worker would have to read a relations/blockedBy field from the same `get_issue` payload (or follow-up reads) and append a new flag (e.g. `--blocked-open`) to the step-3 command, exactly as `--assigned` is conditionally appended today.

**Evidence:**

```js
1. Fetch the ticket: mcp__linear__get_issue (identifier ${t.id}). Read its status name and
   whether it is assigned (assignee non-null). Retry once on failure.
...
     python3 scripts/qrspi_resolve.py --ticket ${t.id} --linear-status "<status>" --ticket-content-file ${ticketFile}

   Replace <status> with the Linear status name from step 1. If (and only if) step 1 found the
   ticket assigned, also append the flag  --assigned  to that command.
```

— `.claude/workflows/qrspi-batch.js:319-334`
**Dependencies:** Upstream: `mcp__linear__get_issue` (Linear MCP). Downstream: `scripts/qrspi_resolve.py` CLI (consumes `--linear-status`, `--assigned`). The worker output is parsed by `parseResolveEnvelope` (`.claude/workflows/qrspi-batch.js:127-144`).
**Implicit contracts:** The worker returns the script's JSON stdout verbatim as plain text (no StructuredOutput); the JS never re-derives Linear facts. Boolean Linear facts are passed as presence-only CLI flags (`--assigned` appended only when true), not as `--assigned true/false`.

## Q2: How does `qrspi_resolve.py` build the `state` dict today (which fields it sets and how each reaches `build_state`/`resolve`), so a new `state["blockedOpen"]` key can be threaded the same way?

**Answer:** `qrspi_resolve.py` does NOT itself assemble the `state` dict — it delegates entirely to `qrspi_pr_state.build_state(owner, repo, ticket, assigned, linear_status, trunk)`, which returns the full state dict, then passes that straight to `resolve(state)`. So `assigned` and `linear_status` arrive in `qrspi_resolve.py` as `args.assigned` / `args.linear_status` and are forwarded as positional args into `build_state`, which places them into the returned dict as `state["assigned"]` and `state["linearStatus"]` (see Q3). A new `blockedOpen` would follow the identical path: a new `args.blocked_open` in `qrspi_resolve.py` → new param on `build_state` → new key in the returned state dict.

**Evidence:**

```python
state = build_state(owner, repo, args.ticket, args.assigned, args.linear_status,
                    trunk=args.trunk)
decision = resolve(state)
worktree = setup_worktree(args.ticket, trunk=args.trunk,
                          create_design=(decision["action"] == "run_design"))
```

— `scripts/qrspi_resolve.py:328-332`
**Dependencies:** `qrspi_resolve.py` imports `build_state` from `qrspi_pr_state` and `resolve` from `qrspi_resolve_state` (`scripts/qrspi_resolve.py:44-45`). The decision is consumed locally to gate `setup_worktree` (only `run_design` provisions a branch).
**Implicit contracts:** `qrspi_resolve.py` reuses the tested pure logic rather than re-deriving state. The state dict is the single object handed to `resolve`; any new field must be set inside `build_state` to reach `resolve`.

## Q3: How is the `assigned`/`linearStatus` data carried from the Linear read through to `qrspi_resolve_state.py` — via CLI flags, JSON envelope, or environment — and what is the exact serialization format a `--blocked-open` flag would follow?

**Answer:** Via CLI flags into `qrspi_resolve.py` (`--assigned`, store_true boolean; `--linear-status`, string default `""`), forwarded positionally to `build_state`, which writes them into the state dict as `"assigned": assigned` and `"linearStatus": linear_status`. That dict is the in-process object passed to `resolve` — there is no JSON envelope or environment between `build_state` and `resolve` (they run in the same process). A `--blocked-open` flag would mirror `--assigned` exactly: an `argparse` `action="store_true"` boolean on `qrspi_resolve.py`, forwarded into `build_state`, serialized as a state key like `"blockedOpen": blocked_open`.

**Evidence:**

```python
    return {
        "ticketId": ticket,
        "assigned": assigned,
        "linearStatus": linear_status,
        "phases": {
            "design": phase_pr("design"),
            "plan": phase_pr("plan"),
            "implementation": { ... },
        },
    }
```

— `scripts/qrspi_pr_state.py:317-331`
(flag parsing: `scripts/qrspi_resolve.py:308-311`; `build_state` signature: `scripts/qrspi_pr_state.py:276`)
**Dependencies:** `qrspi_pr_state.build_state` is the single producer of the state dict for both the standalone `qrspi_pr_state.py --owner/--repo/...` CLI path (lines 334-350) and the one-shot `qrspi_resolve.py` path.
**Implicit contracts:** `assigned` is a Python bool; `linearStatus` is a plain string (empty string when absent). `resolve` reads them by key name (`state.get("assigned")`, `state.get("linearStatus")`). Note: `qrspi_pr_state.py` also has its OWN `--assigned`/`--linear-status` argparse (lines 339-341) used when invoked standalone; both entry points must stay in sync if a new flag is added.

## Q4: What is the current command-line/argument signature of `qrspi_resolve.py`, and how are existing boolean flags parsed so a `--blocked-open` flag can be added consistently?

**Answer:** `qrspi_resolve.py` uses `argparse` with: `--ticket` (required), `--assigned` (`action="store_true"`, the only boolean), `--linear-status` (string, default `""`), `--ticket-content-file` (string, default `""`), `--trunk` (string, default `"main"`). A `--blocked-open` boolean would be added as another `action="store_true"` flag and forwarded into `build_state`.

**Evidence:**

```python
parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-21")
parser.add_argument("--assigned", action="store_true",
                    help="Ticket is assigned to a user (from Linear, supplied by caller)")
parser.add_argument("--linear-status", default="",
                    help="Current Linear status name (from Linear, supplied by caller)")
parser.add_argument("--ticket-content-file", default="", ...)
parser.add_argument("--trunk", default="main", help="Trunk branch (default: main)")
```

— `scripts/qrspi_resolve.py:307-317`
**Dependencies:** `argparse` (stdlib). The parsed `args` are consumed in `main()` (`scripts/qrspi_resolve.py:319-337`).
**Implicit contracts:** Booleans are presence-flags (`store_true`), so the caller appends the flag only when true — matching the `--assigned` convention in the batch prompt (Q1). `argparse` auto-maps `--blocked-open` to `args.blocked_open`.

## Q5: What fields does `mcp__linear__get_issue` return in its payload regarding relations and blocker statuses, and does a single call expose each blocker's status type or is a follow-up per-blocker read required?

**Answer:** NOT FOUND in the codebase. The codebase never inspects relations/blockedBy fields of a `get_issue` payload — the only documented use of `get_issue` is reading the status name and assignee (`.claude/workflows/qrspi-batch.js:319-320`). The exact relations schema and whether a single call exposes each blocker's status type is a property of the Linear MCP server, which is outside `REPO_ROOT` and cannot be determined from this repository. Searches attempted: `grep -rn -i "blockedBy\|relations\|relation\|blocker"` across `.claude/workflows/qrspi-batch.js`, `scripts/qrspi_resolve.py`, `scripts/qrspi_resolve_state.py`, `scripts/qrspi_pr_state.py` — zero matches. No fixture, no schema, no example payload for relations exists in-repo.

**Evidence:**

```js
1. Fetch the ticket: mcp__linear__get_issue (identifier ${t.id}). Read its status name and
   whether it is assigned (assignee non-null). Retry once on failure.
```

— `.claude/workflows/qrspi-batch.js:319-320` (the entire current contract with `get_issue`)
**Dependencies:** `mcp__linear__get_issue` is provided by the `linear` MCP server (`.mcp.json`), external to `REPO_ROOT`.
**Implicit contracts:** The repo treats `get_issue` as a source for `status` + `assignee` only; any blocker-status logic is net-new and the payload shape must be confirmed against the live Linear MCP (not derivable here).

## Q6: What is the function signature and parameter set of `build_state` and `resolve` in the resolver, and how would `blockedOpen` be added without altering existing callers?

**Answer:** `resolve(state)` takes a single dict arg and reads everything by key (`state.get(...)`), so a new `state["blockedOpen"]` key is purely additive — no signature change, no caller change. `build_state(owner, repo, ticket, assigned, linear_status, trunk="main")` is the producer of that dict; adding `blocked_open=False` as a new keyword-defaulted parameter and writing `"blockedOpen": blocked_open` into the returned dict keeps both existing callers (`qrspi_resolve.py` and the standalone `qrspi_pr_state.py` CLI) working unchanged because the new param defaults to `False`.

**Evidence:**

```python
def resolve(state):
    """Pure decision function. Returns a decision dict (see module docstring)."""
    phases = state.get("phases", {})
    existing = [p for p in PHASES if phase_exists(phases, p)]
```

— `scripts/qrspi_resolve_state.py:85-88`

```python
def build_state(owner, repo, ticket, assigned, linear_status, trunk="main"):
```

— `scripts/qrspi_pr_state.py:276`
**Dependencies:** `resolve` callers: `qrspi_resolve.py:330`, plus the test suite. `build_state` callers: `qrspi_resolve.py:328`, `qrspi_pr_state.py:347`.
**Implicit contracts:** `resolve` is pure and reads state by key with `.get(...)` defaults — so missing keys default safely (e.g. `state.get("blockedOpen")` is falsy when absent), making a new key backward-compatible without touching old states.

## Q7: Where exactly is the entry-gate branch (`if "design" not in existing`) located in the resolver, and what conditions does it currently evaluate before returning `run_design` vs `entry_blocked`?

**Answer:** The entry gate is the FIRST branch in `resolve()`, at `scripts/qrspi_resolve_state.py:101-107`. It fires only when no design phase exists yet (`"design" not in existing`). Inside, it returns `run_design` iff `state.get("assigned")` is truthy AND `state.get("linearStatus") == "Selected"`; otherwise it returns `entry_blocked`. This is the ONLY place Linear facts are consulted (comment line 101: "Linear is read ONLY here"). A `blockedOpen` check would slot into this branch: even when assigned+Selected, an open blocker should route to `entry_blocked` (or a more specific blocked reason).

**Evidence:**

```python
    # 1. Entry gate — nothing exists yet. Linear is read ONLY here.
    if "design" not in existing:
        if state.get("assigned") and state.get("linearStatus") == "Selected":
            return decision("run_design", phase="design",
                            reason="Entry gate satisfied (assigned + Selected); no design branch yet.")
        return decision("entry_blocked",
                        reason="No design branch and ticket is not assigned+Selected; nothing begins.")
```

— `scripts/qrspi_resolve_state.py:101-107`
**Dependencies:** Depends on `existing` (computed at line 88, Q8) and `state["assigned"]`/`state["linearStatus"]`.
**Implicit contracts:** Entry gate is gated on `"design" not in existing`, so once any real design branch exists this branch is skipped entirely — blocker checks added here would automatically be ignored for in-flight tickets (satisfies the Q8 "consulted ONLY when design absent" requirement for free).

## Q8: How is `existing` (the set of present branches/phases) computed, so the resolver can confirm that blocking is consulted ONLY when `design` is absent and ignored once a `design` branch exists?

**Answer:** In `resolve`, `existing` is a list comprehension over the fixed `PHASES = ["design", "plan", "implementation"]`, keeping each phase whose `phase_exists(phases, p)` is True. `phase_exists` returns `phases[name]["branchExists"]`. The `branchExists` flag is set upstream in `build_state` only for branches that are REAL — i.e. at least one commit ahead of trunk (`real_branches` / `_commits_ahead`), which filters out the empty placeholder branch worktree-setup leaves on a fresh ticket. So `"design" not in existing` is true exactly when there is no design branch carrying real work — which is the entry-gate window. Once a real design branch exists, the gate (and any blocker check inside it) is skipped.

**Evidence:**

```python
def phase_exists(phases, name):
    """A phase exists once its branch exists. ..."""
    return bool(phases.get(name, {}).get("branchExists", False))
...
    phases = state.get("phases", {})
    existing = [p for p in PHASES if phase_exists(phases, p)]
```

— `scripts/qrspi_resolve_state.py:59-62, 87-88`

```python
    ahead = {b: _commits_ahead(b, trunk) for b in branches}
    real = real_branches(branches, ahead)
    def phase_pr(name):
        head = "%s/%s" % (ticket, name)
        exists = head in real
        ...
        pr["branchExists"] = exists
```

— `scripts/qrspi_pr_state.py:284-293`
**Dependencies:** `phase_exists` ← `branchExists` ← `real_branches` ← `_commits_ahead` (trunk-relative). For implementation, `branchExists` is `bool(real_snums)` (`qrspi_pr_state.py:325`).
**Implicit contracts:** A phase "exists" only if its branch is ≥1 commit ahead of trunk (an empty design branch does NOT count). Placing the blocker check inside the `if "design" not in existing` branch guarantees it is consulted only pre-design and ignored thereafter.

## Q9: What is the current shape of the `decision(...)` return for `entry_blocked`, including how the `reason` string is populated, so blocker identifiers can be named in the reason?

**Answer:** `decision(action, **kw)` is a nested helper in `resolve` that always returns a dict with fixed keys: `action`, `phase`, `nextPhase`, `resetToPhase`, `discardPhases` (default `[]`), and `reason` (default `""`). For `entry_blocked` today, only `action` and `reason` are set — `reason` is a fixed string literal `"No design branch and ticket is not assigned+Selected; nothing begins."`. To name blockers, the call would pass a `reason=` string interpolating blocker identifiers (e.g. via `%`-formatting, the convention used everywhere else in this function — see the `reset` reason at lines 116-117).

**Evidence:**

```python
    def decision(action, **kw):
        out = {
            "action": action,
            "phase": kw.get("phase"),
            "nextPhase": kw.get("nextPhase"),
            "resetToPhase": kw.get("resetToPhase"),
            "discardPhases": kw.get("discardPhases", []),
            "reason": kw.get("reason", ""),
        }
        return out
```

— `scripts/qrspi_resolve_state.py:90-99`
**Dependencies:** Every action in `resolve` flows through this helper. The orchestrator reads `decision.reason` for logging (`qrspi-batch.js:847`, Q15) and `decision.action` for dispatch (`qrspi-batch.js:846-865`).
**Implicit contracts:** `reason` is a free-form human-readable string surfaced in batch logs; identifiers embedded in it are observability only (no consumer parses `reason`). The dict shape is fixed — adding blocker IDs into `reason` requires no new key, but if a structured `blockers` field were wanted it would be a new key NOT in `parseResolveEnvelope`'s validation (which only checks `action`).

## Q10: How does the resolver currently behave when `linearStatus` is absent, null, or not `"Selected"` — and how would a `blockedOpen` flag interact with those cases at the entry gate?

**Answer:** The entry gate requires `state.get("linearStatus") == "Selected"` (strict string equality). Absent/null/empty (`""`, the `--linear-status` default) or any non-`"Selected"` value fails this and returns `entry_blocked` (covered by tests "not assigned -> blocked" and "assigned but not Selected -> blocked"). A `blockedOpen` flag would be an ADDITIONAL gate condition: even when `assigned and linearStatus == "Selected"`, a truthy `blockedOpen` should override the `run_design` path and return `entry_blocked` (or a blocked-specific reason). Because the existing condition already short-circuits to `entry_blocked` for non-Selected/unassigned tickets, `blockedOpen` only matters in the otherwise-passing (assigned+Selected) case.

**Evidence:**

```python
        if state.get("assigned") and state.get("linearStatus") == "Selected":
            return decision("run_design", phase="design", ...)
        return decision("entry_blocked", ...)
```

— `scripts/qrspi_resolve_state.py:103-107`
(tests: `scripts/qrspi_resolve_state_test.py:45-55`)
**Dependencies:** `state["linearStatus"]` originates from `--linear-status` (default `""`) via `build_state`.
**Implicit contracts:** Comparison is exact-string `== "Selected"` — case/whitespace sensitive; the caller is responsible for passing the verbatim Linear status name. `state.get(...)` makes a missing key safely falsy. A new `blockedOpen` gate must be combined so it can only BLOCK (never unblock) — it adds a failure path inside the assigned+Selected branch.

## Q11: Which Linear status types does the codebase already recognize as terminal, and where is that mapping defined, so a blocker can be classified "open unless `completed`/`canceled`"?

**Answer:** NOT FOUND — the codebase has NO mapping of Linear status TYPES (e.g. `completed`/`canceled`/`started`/`backlog`) and no notion of "terminal" Linear statuses. The only Linear status logic is the literal name comparison `linearStatus == "Selected"` at the entry gate (Q10). The batch workflow enumerates status NAMES it queries (`STATUSES = ['Selected', 'Design Review', 'Plan Review', 'Code Review']`, `qrspi-batch.js:61`) and a reporting projection toward `Done`, but these are display names, not Linear `statusType` enum values, and none is classified as "terminal" for blocker purposes. Classifying a blocker as "open unless completed/canceled" would require net-new logic; the worker would need to read each blocker's status type from the `get_issue`/relations payload (whose shape is unconfirmed — Q5) and the open/closed determination would have to be decided there, then collapsed into the single `--blocked-open` boolean before `qrspi_resolve.py`. Searches: `grep -rn -i "completed\|canceled\|cancelled\|terminal\|statusType"` over the four core files — only matches are unrelated uses of the word "terminal" (the pr-summary.md "terminal artifact").

**Evidence:**

```js
const STATUSES = input?.statuses ?? ['Selected', 'Design Review', 'Plan Review', 'Code Review']
```

— `.claude/workflows/qrspi-batch.js:61`
**Dependencies:** Status NAMES are used to query Linear (the `list:` agents, `qrspi-batch.js:779-787`) and for best-effort reporting projection. No `statusType` enum is referenced anywhere in-repo.
**Implicit contracts:** All status handling in-repo is by exact display NAME, not Linear's `statusType`. Any "open vs terminal blocker" classification is new and must be owned by the resolve worker (reading the live MCP payload), then reduced to one boolean — consistent with how `assigned`/`linearStatus` are reduced before the script boundary.

## Q12: How does the resolve worker handle a `get_issue` call that returns no relations field or an empty `blockedBy` list, and what default does that produce for the `--blocked-open` flag?

**Answer:** NOT FOUND (no current behavior) — the worker never reads relations/`blockedBy` today (Q1, Q5), so there is no existing handling of an absent relations field or empty `blockedBy`. By analogy with the established pattern, a `--blocked-open` boolean would be a presence-flag: the worker appends it ONLY when it determines an open blocker exists; absent/empty relations means the flag is simply not appended, and `args.blocked_open` defaults to `False` (no blocker → not blocked → entry gate proceeds as today). This mirrors how `--assigned` is omitted when the assignee is null. The `argparse` default for a `store_true` flag is `False`, and `state.get("blockedOpen")` would be falsy when the key is absent — so an empty/missing blocker list naturally yields the non-blocked default.

**Evidence:**

```js
   Replace <status> with the Linear status name from step 1. If (and only if) step 1 found the
   ticket assigned, also append the flag  --assigned  to that command.
```

— `.claude/workflows/qrspi-batch.js:333-334` (the conditional-append pattern a `--blocked-open` flag would follow)
**Dependencies:** Worker → `qrspi_resolve.py` flag boundary. `store_true` default is stdlib `argparse` behavior.
**Implicit contracts:** Booleans are presence-only flags; "absence == false == safe default." The fail-safe direction is NOT to block: missing/empty relations must default to NOT blocked, so a relations-read failure cannot strand an otherwise-ready ticket (consistent with the codebase's "a failed Linear read never blocks work" stance for reporting — though note the entry gate itself is the one place Linear can block).

## Q13: What is the existing test structure in `scripts/qrspi_resolve_state_test.py` for constructing entry-gate states (assigned + Selected), so new blocked/unblocked/in-flight cases follow the same stdlib-only pattern?

**Answer:** Stdlib-only, assert-based (no pytest). Tests are declared via `case(name, st, expect)` which appends to a global `CASES` list; `run()` iterates, calls `resolve(st)`, and asserts each key in `expect` matches. States are built by the `state(assigned=True, linear="Selected", phases=None)` factory (defaults to assigned+Selected with empty phases). Entry-gate cases pass `phases={}` so no phase exists and the entry branch fires. Phase fixtures use helpers `_phase(...)`, `_impl(...)`, `_slice(...)`. A new blocked case would call `state(assigned=True, linear="Selected", phases={})` plus a new `blockedOpen=True` field (requiring a small extension to the `state()` factory to thread `blockedOpen`).

**Evidence:**

```python
def state(assigned=True, linear="Selected", phases=None):
    return {"ticketId": "RUS-1", "assigned": assigned, "linearStatus": linear,
            "phases": phases or {}}
...
def case(name, st, expect):
    CASES.append((name, st, expect))
...
case("entry: assigned + Selected -> run_design",
     state(assigned=True, linear="Selected", phases={}),
     {"action": "run_design", "phase": "design"})
```

— `scripts/qrspi_resolve_state_test.py:32-55`
**Dependencies:** Imports only `resolve` from `qrspi_resolve_state` and stdlib `sys`. Run with `python3 scripts/qrspi_resolve_state_test.py`; exits 1 on first failure key.
**Implicit contracts:** The `state()` factory is the canonical entry-gate constructor; adding a `blockedOpen` param there (defaulting False) keeps all existing cases green while enabling blocked cases. `expect` is a partial dict — only the listed keys are asserted, so a case may assert just `{"action": ..., "reason": ...}`.

## Q14: How do current tests assert on the returned `action` and `reason` fields of a decision, so a `blocked+Selected → entry_blocked` assertion (including the blocker named in `reason`) can match existing conventions?

**Answer:** `run()` checks, for each `(key, want)` in the case's `expect` dict, that `got.get(key) != want` → fail. It is EXACT EQUALITY per key. Existing entry-gate cases assert only `{"action": "entry_blocked"}` — no current test asserts on `reason`, and the equality check means a `reason` assertion would require the FULL string to match verbatim (no substring matching exists). To assert "blocker named in reason," a test would need either the exact full reason string, or the test harness would need a substring/contains helper added (none exists today). The simplest convention-matching approach: assert `{"action": "entry_blocked"}` and, if reason content matters, pass the exact full reason string in `expect`.

**Evidence:**

```python
    for name, st, expect in CASES:
        got = resolve(st)
        for key, want in expect.items():
            if got.get(key) != want:
                print("FAIL: %s\n      key %r: expected %r, got %r ...")
                failures += 1
                break
```

— `scripts/qrspi_resolve_state_test.py:191-198`
**Dependencies:** Pure equality via `dict.get`. No assertion-library, no regex/substring support.
**Implicit contracts:** Each `expect` key is matched by `==` against `got.get(key)`. Asserting on `reason` is all-or-nothing exact-string; a "blocker named in reason" test must therefore pin the entire reason string (brittle) unless a contains-style check is introduced. Existing convention is to assert `action` (+ `phase`/`nextPhase`/`resetToPhase`/`discardPhases`) and NOT `reason`.

## Q15: How does `qrspi-batch.js` currently surface the resolver's decision and `reason` per ticket (logging, console output, or run summary), so an `entry_blocked` outcome with named open blockers is visible in an autonomous run?

**Answer:** In the per-ticket main loop, after a successful resolve+restack, the orchestrator logs `decision=<action> — <reason>` via `log(...)`. The full `r.decision.reason` string is printed verbatim, so any blocker identifiers embedded in the `entry_blocked` reason (Q9) would appear there. `entry_blocked` then falls through the dispatch `switch` to the default/`wait` arm, which calls `skip(t, r.decision, ...)` (returns `{ticketId, action, summary}`) and logs `skipped (entry_blocked)`. The decision line is the primary visibility surface; `skip` records the action+summary into the `results` array used for the run summary.

**Evidence:**

```js
    const a = r.decision.action
    log(`  ${t.id}: decision=${a} — ${r.decision.reason}`)
    let res
    switch (a) {
      ...
      case 'wait':
      case 'entry_blocked':
      default:
        res = skip(t, r.decision, `Skipped (${a}): ${r.decision.reason}`)
        log(`  ${t.id}: skipped (${a})`)
    }
    results.push(res)
```

— `.claude/workflows/qrspi-batch.js:846-866`
(`skip` helper: `qrspi-batch.js:243-245`)
**Dependencies:** `log()` is the workflow logging primitive; `results[]` feeds the final run summary. `skip(t, decision, note)` returns `{ticketId: t.id, action: decision.action, summary: note}`.
**Implicit contracts:** `reason` is logged as opaque text — embedding open-blocker identifiers in the `entry_blocked` reason string makes them visible with no additional plumbing. `entry_blocked` shares the default/wait dispatch arm: it is intentionally a no-op (skip), so a blocked ticket is logged and recorded but never advanced.

---

## Discovered Patterns

- **Pure-logic core + thin I/O shell.** All decision logic lives in pure, unit-tested functions (`resolve`, `build_state` helpers, `parse_pr_nodes`, `select_pr`); subprocess/MCP calls are isolated and explicitly NOT unit-tested. New entry-gate logic belongs in `resolve` (pure) and gets a stdlib-only test case.
- **Linear facts reduced to booleans/strings BEFORE the script boundary.** The weak local worker model cannot hand-assemble JSON, so each Linear fact is collapsed to a presence-flag (`--assigned`) or a string (`--linear-status`) that `argparse` parses. A blocker signal should follow the same reduction: worker computes "is there an open blocker?" → single `--blocked-open` boolean. (See `~/.agents` memory: Ollama worker StructuredOutput gap, path-mangling.)
- **Presence-flag convention.** Booleans are `action="store_true"`; callers append the flag only when true; absence == false == safe default.
- **Linear reads ONLY at the entry gate.** `resolve` consults `assigned`/`linearStatus` solely in the `if "design" not in existing` branch (line 101 comment). Any blocker gate placed there is automatically ignored once design exists — satisfying Q8's "consulted only pre-design" requirement with zero extra guarding.
- **Two `build_state`/flag entry points.** Both `qrspi_resolve.py` (one-shot) and `qrspi_pr_state.py` (standalone CLI) parse `--assigned`/`--linear-status` and call `build_state`. A new flag added to one must be mirrored in the other to keep them consistent.
- **`reason` is opaque observability.** No consumer parses `reason`; it is logged verbatim. Naming blockers there needs no schema change. The envelope validator (`parseResolveEnvelope`) checks only `decision.action` against `RESOLVE_ACTIONS`.
- **Fail-safe direction is "do not block."** Missing/unreadable Linear data degrades to empty-string/false defaults across the gather (`_git_show`→"", `_commits_ahead`→0). A blocker default should likewise be "not blocked" so a relations-read miss cannot strand a ready ticket.

## Inconsistencies

- **No Linear status-TYPE model exists, but the entry gate hard-codes a status NAME.** The code compares `linearStatus == "Selected"` (display name) and never references Linear's `statusType` enum (`backlog`/`unstarted`/`started`/`completed`/`canceled`). The ticket-area premise of classifying a blocker "open unless completed/canceled" has NO existing scaffolding to build on — it is entirely net-new, and the open/closed determination must be made worker-side from a `get_issue`/relations payload whose schema is unverified in-repo (Q5).
- **Duplicated flag parsing.** `--assigned`/`--linear-status` are defined independently in `qrspi_resolve.py:308-311` and `qrspi_pr_state.py:339-341`. The docstrings/help text are near-identical but the definitions are not shared, so a new flag risks being added to only one path.
- **Tests never assert on `reason`.** Every existing case asserts `action` (and structural keys) but not `reason`, and the harness only supports exact-equality (no substring). A requirement to verify "the blocker is named in `reason`" cannot be satisfied with the current test harness without either pinning the entire reason string (brittle) or adding a contains-style assertion helper.
- **`real_branches` gate is documented as reliable only for design.** The trunk-ahead gate "reliably catches an empty *design* branch" but an empty plan/slice branch "would read as real" (`qrspi_pr_state.py:206-223`). This is noted only as a caveat the commit workers guard manually — relevant because the entry-gate window depends on design `branchExists`, which the gate handles correctly, but the asymmetry is an existing known gap.
