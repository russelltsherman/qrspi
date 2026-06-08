# Questions — qrspi resolver: respect Linear blockedBy relations at the entry gate

**Ticket:** RUS-50
**Generated:** 2026-06-08T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the resolve worker's `get_issue` call currently extract `assigned` and `linearStatus`, and where in that path would a `blockedBy`-derived flag be assembled before invocation of `qrspi_resolve.py`?
  **Target:** the resolve prompt in `.claude/workflows/qrspi-batch.js`
- Q2: How does `qrspi_resolve.py` build the `state` dict today (which fields it sets and how each reaches `build_state`/`resolve`), so a new `state["blockedOpen"]` key can be threaded the same way?
  **Target:** `scripts/qrspi_resolve.py`
- Q3: How is the `assigned`/`linearStatus` data carried from the Linear read through to `qrspi_resolve_state.py` — via CLI flags, JSON envelope, or environment — and what is the exact serialization format a `--blocked-open` flag would follow?
  **Target:** `scripts/qrspi_resolve.py` and `scripts/qrspi_resolve_state.py`

## API Surface

- Q4: What is the current command-line/argument signature of `qrspi_resolve.py`, and how are existing boolean flags parsed so a `--blocked-open` flag can be added consistently?
  **Target:** the argument-parsing section of `scripts/qrspi_resolve.py`
- Q5: What fields does `mcp__linear__get_issue` return in its payload regarding relations and blocker statuses, and does a single call expose each blocker's status type or is a follow-up per-blocker read required?
  **Target:** the module responsible for the Linear `get_issue` read in `.claude/workflows/qrspi-batch.js`
- Q6: What is the function signature and parameter set of `build_state` and `resolve` in the resolver, and how would `blockedOpen` be added without altering existing callers?
  **Target:** `scripts/qrspi_resolve_state.py`

## State Management

- Q7: Where exactly is the entry-gate branch (`if "design" not in existing`) located in the resolver, and what conditions does it currently evaluate before returning `run_design` vs `entry_blocked`?
  **Target:** `scripts/qrspi_resolve_state.py`
- Q8: How is `existing` (the set of present branches/phases) computed, so the resolver can confirm that blocking is consulted ONLY when `design` is absent and ignored once a `design` branch exists?
  **Target:** the artifact/branch-detection logic feeding `scripts/qrspi_resolve_state.py`
- Q9: What is the current shape of the `decision(...)` return for `entry_blocked`, including how the `reason` string is populated, so blocker identifiers can be named in the reason?
  **Target:** the `decision` helper in `scripts/qrspi_resolve_state.py`

## Edge Cases

- Q10: How does the resolver currently behave when `linearStatus` is absent, null, or not `"Selected"` — and how would a `blockedOpen` flag interact with those cases at the entry gate?
  **Target:** the entry-gate branch of `scripts/qrspi_resolve_state.py`
- Q11: Which Linear status types does the codebase already recognize as terminal, and where is that mapping defined, so a blocker can be classified "open unless `completed`/`canceled`"?
  **Target:** the module responsible for interpreting Linear status in `.claude/workflows/qrspi-batch.js`
- Q12: How does the resolve worker handle a `get_issue` call that returns no relations field or an empty `blockedBy` list, and what default does that produce for the `--blocked-open` flag?
  **Target:** the resolve prompt in `.claude/workflows/qrspi-batch.js`

## Testing

- Q13: What is the existing test structure in `scripts/qrspi_resolve_state_test.py` for constructing entry-gate states (assigned + Selected), so new blocked/unblocked/in-flight cases follow the same stdlib-only pattern?
  **Target:** `scripts/qrspi_resolve_state_test.py`
- Q14: How do current tests assert on the returned `action` and `reason` fields of a decision, so a `blocked+Selected → entry_blocked` assertion (including the blocker named in `reason`) can match existing conventions?
  **Target:** `scripts/qrspi_resolve_state_test.py`

## Observability

- Q15: How does `qrspi-batch.js` currently surface the resolver's decision and `reason` per ticket (logging, console output, or run summary), so an `entry_blocked` outcome with named open blockers is visible in an autonomous run?
  **Target:** the per-ticket reporting/logging path in `.claude/workflows/qrspi-batch.js`
