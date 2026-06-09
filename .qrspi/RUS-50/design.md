# Design — qrspi resolver: respect Linear blockedBy relations at the entry gate

**Ticket:** RUS-50
**Research basis:** research.md @ 2026-06-08T00:00:00Z
**Generated:** 2026-06-08T00:00:00Z
**Status:** revised (open questions resolved per reviewer answers on PR #164)

## Current State

The entry gate is the first branch inside `resolve()` in `scripts/qrspi_resolve_state.py`, firing only when no design phase exists yet (`if "design" not in existing`); it returns `run_design` iff `state.get("assigned")` is truthy AND `state.get("linearStatus") == "Selected"`, otherwise `entry_blocked` (ref: Q7). This is the only place Linear facts are consulted — the comment on line 101 reads "Linear is read ONLY here" (ref: Q7). The `existing` list is computed over the fixed `PHASES` keeping each phase whose `phase_exists(phases, p)` is true, where `phase_exists` returns `branchExists`, set upstream only for branches at least one commit ahead of trunk — so an empty placeholder design branch does not count as existing (ref: Q8).

The resolve worker is a natural-language agent prompt in `resolveTicket(t)`/the batch resolve step; step 1 instructs it to call `mcp__linear__get_issue` and read exactly two facts — the status name and whether an assignee is non-null — then conditionally append `--assigned` and substitute `--linear-status "<status>"` into the `qrspi_resolve.py` invocation (ref: Q1). Nothing in JS re-derives Linear facts; the worker reads the MCP payload itself and the script output is parsed verbatim by `parseResolveEnvelope`, which validates only `decision.action` (ref: Q1, ref: Q9).

`qrspi_resolve.py` does not assemble the state dict; it forwards `args.assigned` / `args.linear_status` positionally into `qrspi_pr_state.build_state(...)`, which writes them as `state["assigned"]` / `state["linearStatus"]` and returns the dict handed straight to `resolve(state)` (ref: Q2, ref: Q3). Flags are parsed with `argparse`; `--assigned` is the only boolean (`action="store_true"`), `--linear-status` defaults to `""` (ref: Q4). `resolve(state)` reads everything by key with `.get(...)`, so a missing key is safely falsy and a new key is purely additive with no signature or caller change (ref: Q6). The `decision(action, **kw)` helper returns a fixed-key dict (`action`, `phase`, `nextPhase`, `resetToPhase`, `discardPhases`, `reason`); for `entry_blocked` only `action` and a fixed literal `reason` are set today (ref: Q9).

There is no Linear status-TYPE model in the codebase — all status handling is by exact display NAME (`linearStatus == "Selected"`), and no `statusType` enum (`completed`/`canceled`/...) is referenced anywhere; classifying a blocker "open unless completed/canceled" is entirely net-new (ref: Q11). The exact relations/`blockedBy` schema returned by `mcp__linear__get_issue` is NOT determinable in-repo — no fixture, schema, or example payload exists; the repo has never read relations (ref: Q5). Boolean flags are presence-only ("absence == false == safe default"), and the fail-safe direction across the gather is "do not block" (ref: Q12). The test suite is stdlib-only and assert-based: a `state(assigned, linear, phases)` factory plus a `case(name, st, expect)` list, with `run()` doing exact-equality per `expect` key; no current case asserts on `reason` and no substring matching exists (ref: Q13, ref: Q14). The batch loop logs `decision=<action> — <reason>` verbatim and routes `entry_blocked` through the default/`wait` skip arm (a no-op) (ref: Q15).

## Desired End State

The autonomous batch must not start a ticket whose Linear blockers are still open, while preserving the "Linear read ONLY at entry" invariant and the pure-decision model.

- **AC1 — `assigned + Selected + blockedOpen` → `entry_blocked` (does not start design):** the entry-gate branch gains a third condition. When `assigned` and `linearStatus == "Selected"` are both satisfied but `state.get("blockedOpen")` is truthy, `resolve` returns `entry_blocked` with a reason naming ALL open blocker(s) (RD4), instead of `run_design`. The open blockers' identifiers travel alongside the boolean as `state.get("blockedBy")` (a list/string the worker supplies); `reason` folds them in so each open blocker's identifier is a substring of `reason` (RD2 — asserted via a `contains` helper in the test).
- **AC2 — `assigned + Selected` with all blockers completed → `run_design` as today:** when `blockedOpen` is falsy (the default), the entry gate behaves exactly as it does now. The worker appends `--blocked-open` only when it detects an open blocker, so a fully-unblocked or relation-less ticket leaves the flag absent and `args.blocked_open` defaults to `False`.
- **AC3 — in-flight ticket (design branch exists) with an open blocker → decision unaffected:** because the blocker check lives inside the `if "design" not in existing` branch, it is automatically skipped once a real design branch exists. No downstream path (`wait`/`revise`/`reset`/`advance`/`land`) reads `blockedOpen`.
- **AC4 — no change to `wait`/`revise`/`reset`/`advance`/`land` paths:** `blockedOpen` is consulted in exactly one expression in the entry-gate branch and nowhere else.

The resolve worker reads the ticket's `blockedBy` relations from `mcp__linear__get_issue`, determines whether any blocker is in a non-completed/non-canceled state, and collapses that to a single `--blocked-open` presence flag before the script boundary — mirroring how `--assigned` is reduced today.

## Delta

**Modified — `scripts/qrspi_resolve_state.py` (the only behavior change):** Add a `blockedOpen` check inside the existing entry-gate branch. When `assigned and linearStatus == "Selected"`, branch further on `state.get("blockedOpen")`: if truthy, return `entry_blocked` with a reason that names ALL open blockers (RD4) by folding `state.get("blockedBy")` (the worker-supplied identifier list, falling back to an empty list) into the reason string; otherwise return `run_design` as today. No new function, no signature change — `resolve` already reads state by key.

**Modified — `scripts/qrspi_pr_state.py`:** Add `blocked_open=False` and `blocked_by=()` (or `None`) as keyword-defaulted parameters to `build_state(...)` and write `"blockedOpen": blocked_open` and `"blockedBy": list(blocked_by or [])` into the returned state dict. The defaults keep both existing callers green.

**Modified — `scripts/qrspi_resolve.py`:** Add `--blocked-open` (`action="store_true"`) and `--blocked-by` (repeatable / comma-joined, defaulting to empty) to argparse and forward `args.blocked_open` / parsed `args.blocked_by` into the `build_state(...)` call.

**Modified — `scripts/qrspi_pr_state.py` standalone CLI:** Add matching `--blocked-open` and `--blocked-by` flags to that file's own argparse and thread them into its `build_state(...)` call, keeping the two entry points in sync (ref: Q3, ref: Discovered Patterns "Two build_state entry points").

**Modified — `.claude/workflows/qrspi-batch.js` (resolve prompt):** Extend step 1 to also read `blockedBy` relations from the `get_issue` payload (and any follow-up read needed to obtain each blocker's status type — to be confirmed against the live MCP, RD1), classify a blocker as open unless its status type is `completed`/`canceled`, and treat any unrecognized/unknown status type as open (RD3, fail toward blocking). In step 3 conditionally append `--blocked-open` only when at least one open blocker exists, and pass the identifiers of ALL open blockers via `--blocked-by` (RD4) so the resolver can name them in `reason`.

**Modified — `scripts/qrspi_resolve_state_test.py`:** Extend the `state(...)` factory with a `blockedOpen=False` parameter and add cases — blocked+Selected → `entry_blocked`; unblocked+Selected → `run_design`; in-flight (design branch present) + blocked → unchanged decision. Add a small `contains`-style assertion helper (RD2, reviewer-requested) and one case asserting each open blocker's identifier is a substring of the `entry_blocked` `reason` (the reason lists ALL open blockers per RD4). To make `reason` assertable, the worker must pass the open blockers' identifiers to the script (see the resolve-prompt delta below) so the resolver can fold them into `reason`; the test exercises this via the `blockedOpen` factory carrying the blocker identifier(s).

No new files. No new git queries. The relation-read (worker) part is verified by manual e2e against a real blocked ticket (ref: Q5 — schema unverifiable in-repo).

## Pattern Decisions

### Decision 1: Where the open/closed blocker classification is computed

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Worker computes "any open blocker?" from the MCP payload, passes one `--blocked-open` boolean | Matches the established "Linear facts reduced to booleans before the script boundary" pattern (ref: Discovered Patterns); pure resolver stays trivially testable; no MCP coupling in Python | Worker (weak model) owns the status-type interpretation; not unit-testable in-repo (verified by e2e) |
| B | Pass raw blocker statuses/relations as structured JSON to the script; classify in Python | Classification is unit-testable; richer reason strings | Violates the boolean-reduction pattern; weak worker cannot reliably hand-assemble JSON (ref: Ollama StructuredOutput memory); adds MCP-schema coupling to Python |

**Recommendation:** Option A
**Rationale:** The codebase already reduces every Linear fact to a presence-flag/string before `qrspi_resolve.py` precisely because the local worker model cannot author structured payloads (ref: Q11, ref: Discovered Patterns "Linear facts reduced to booleans"). `--blocked-open` is the exact analogue of `--assigned`. This is the ticket's prescribed approach.
**NEW PATTERN?** No — it reuses the existing presence-flag + boolean-reduction convention.

### Decision 2: Gate placement and the "ignored once in-flight" guarantee

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add the `blockedOpen` check inside the existing `if "design" not in existing` entry-gate branch | "Consulted only pre-design" is satisfied for free (ref: Q7, ref: Q8); single expression changed; AC3/AC4 hold structurally | Reason-string composition for named blockers sits in the hot branch |
| B | Add a separate top-level guard before the entry gate | Slightly more explicit | Risks consulting blocking when design already exists unless re-guarded; duplicates the `"design" not in existing` condition; violates the single-consult invariant |

**Recommendation:** Option A
**Rationale:** The entry-gate branch already fires exactly in the pre-design window because `existing` is trunk-ahead-gated and the empty placeholder design branch does not count (ref: Q8). Nesting the check there means in-flight tickets skip it with zero extra guarding (ref: Discovered Patterns "Linear reads ONLY at the entry gate").
**NEW PATTERN?** No.

### Decision 3: Asserting the blocker is named in `reason`

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Assert only `{"action": "entry_blocked"}` for the blocked case; do not pin `reason` | Matches existing convention (no case asserts `reason`); non-brittle (ref: Q14) | Does not verify the named-blocker requirement in `reason` |
| B | Pin the full exact `reason` string in `expect` | Verifies blocker naming | Brittle — any wording change breaks the test; harness has no substring match (ref: Q14) |
| C | Add a tiny `contains`-style assertion helper to the test harness | Verifies naming without full-string brittleness | New test-harness capability; small scope creep beyond the ticket |

**Decision:** Option C — the reviewer answered "yes" to RD2 (formerly OQ2): the test suite must verify the open-blocker identifier appears in `reason`. We add a small `contains`-style assertion helper to the test harness rather than pinning the full string (Option B is rejected as brittle; Option A under-verifies the named-blocker requirement the reviewer asked for).
**Rationale:** The reviewer explicitly wants in-test verification that an open blocker is named in `reason`. Exact-equality on the full string is brittle (ref: Q14), so the minimal robust path is a substring/`contains` assertion. The harness only supports exact-equality today (ref: Q14), so this introduces one small reusable helper alongside the existing exact-equality `run()` — scoped to a single substring check on `reason`, no broader matcher framework.
**NEW PATTERN?** Yes — a `contains`-style assertion helper in `qrspi_resolve_state_test.py`. Small and reviewer-requested; documented here.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `mcp__linear__get_issue` does not expose each blocker's status type in one call, requiring per-blocker follow-up reads (schema unverified in-repo, ref: Q5) | med | med | Confirm payload shape against the live Linear MCP during worker implementation (RD1: reviewer said "unsure, verify"); the ticket explicitly calls for this verification; worker logic adapts (single call vs. per-blocker read) without touching the Python/test surface |
| Relations-read failure or weak-worker misread strands a ready ticket by spuriously appending `--blocked-open` | low | high | Fail-safe default is "not blocked": the flag is appended ONLY when an open blocker is positively detected; absent/empty/unreadable relations → flag omitted → `run_design` proceeds (ref: Q12, ref: Discovered Patterns "Fail-safe direction is do not block") |
| New flag added to only one of the two `build_state` entry points, desyncing `qrspi_resolve.py` and standalone `qrspi_pr_state.py` (ref: Inconsistencies "Duplicated flag parsing") | med | low | Delta explicitly lists both argparse definitions; a unit test exercising `build_state(..., blocked_open=True)` and the `blockedOpen` state key catches a missing thread |
| Status-type name/casing mismatch — worker compares against wrong terminal values since no in-repo mapping exists (ref: Q11) | med | med | Define the terminal set explicitly as Linear `statusType` values `completed`/`canceled` (per ticket); verify against live MCP in e2e; treat any unrecognized type as open (RD3: reviewer chose "fail toward blocking" — a genuinely-unknown blocker counts as open) |
| `reason` named-blocker assertion proves brittle if pinned to full string | low | low | Use a `contains`-style substring assertion on `reason` (Decision 3, Option C — reviewer-requested), not full-string equality; the test asserts the open blocker's identifier is a substring of `reason`, which survives wording changes |

## Resolved Decisions (reviewer answers to former Open Questions)

The reviewer addressed each open question inline on the design PR (#164). The answers are now binding design decisions:

- **RD1 (was OQ1) — blocker status-type fetch shape: "unsure, verify".** Whether a single `mcp__linear__get_issue` call returns each `blockedBy` blocker's status TYPE (vs. requiring a per-blocker follow-up read) is still not determinable in-repo (ref: Q5). The worker prompt MUST verify the payload shape against the live Linear MCP and adapt (single call vs. per-blocker read) during implementation/e2e. This is a worker-side, MCP-only concern: it does not change the Python or test surface (which consume the already-reduced `--blocked-open`/`--blocked-by` flags), so it does not block this design — it is a verification step the worker phase carries out.
- **RD2 (was OQ2) — verify the blocker identifier appears in `reason`: "yes".** The test suite MUST assert that each open blocker's identifier appears in `reason`. We add a small `contains`-style substring assertion helper to `qrspi_resolve_state_test.py` (Decision 3, Option C) rather than pinning the full brittle string (ref: Q14). This is reflected in the Delta and Decision 3 above.
- **RD3 (was OQ3) — unrecognized blocker status type: "fail toward blocking".** A blocker whose status type is neither `completed`/`canceled` nor a recognized open type counts as OPEN. The worker treats any unknown/unexpected status type as an open blocker (appends `--blocked-open` and includes it in `--blocked-by`). This overrides the generic do-not-block default specifically for the blocker classification: dependency-correctness wins for genuinely-unknown blocker states. (The do-not-block default still applies when relations are absent/empty/unreadable — RD3 only governs a blocker that IS present but has an unrecognized type.)
- **RD4 (was OQ4) — how many blockers to name in `reason`: "all".** The `reason` string lists ALL open blockers, not just the first. The worker passes every open blocker's identifier via `--blocked-by`, and the resolver folds the full list into `reason`. RD2's `contains` test asserts each supplied identifier is a substring of `reason`.
