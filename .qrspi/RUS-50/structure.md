# Structure Outline — qrspi resolver: respect Linear blockedBy relations at the entry gate

**Design basis:** design.md @ 2026-06-08T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## New Types

None. The change is purely additive over the existing untyped `state` dict
(plain `dict[str, Any]`). Two new keys flow through it:

- `state["blockedOpen"]: bool` — true iff the worker positively detected at least one open Linear blocker (default falsy / absent).
- `state["blockedBy"]: list[str]` — identifiers of ALL open blockers (RD4); empty list when none/unknown.

## Modified Types

- `state` dict (the resolver's untyped input) — add key `blockedOpen: bool` and key `blockedBy: list[str]` (ref: design.md §Delta). Read by `.get(...)` so additive, no signature change.

## Contracts

- `resolve(state) -> dict` — UNCHANGED signature. New behavior only inside the existing `if "design" not in existing` entry-gate branch: when `state.get("assigned")` and `state.get("linearStatus") == "Selected"`, branch further on `state.get("blockedOpen")`; if truthy return `entry_blocked` with a `reason` that folds in every identifier from `state.get("blockedBy") or []` (RD2/RD4), else return `run_design` as today.
- `build_state(..., blocked_open=False, blocked_by=None) -> dict` — both entry points (`scripts/qrspi_pr_state.py` and the call site in `scripts/qrspi_resolve.py`) gain keyword-defaulted params; writes `"blockedOpen": blocked_open` and `"blockedBy": list(blocked_by or [])`. Defaults keep existing callers green.
- `qrspi_resolve.py` argparse — add `--blocked-open` (`action="store_true"`) and `--blocked-by` (repeatable/comma-joined, default empty); forward into its `build_state(...)` call.
- `qrspi_pr_state.py` standalone CLI argparse — add matching `--blocked-open` / `--blocked-by`; thread into its own `build_state(...)` call (keeps the two entry points in sync).
- `contains(reason, needle) -> bool` (NEW test helper, RD2) — substring assertion helper in `qrspi_resolve_state_test.py` for verifying each open-blocker identifier appears in `reason` without pinning the full brittle string.

## Slice 1: Resolver blockedOpen gate + state plumbing + tests

**Goal:** End-to-end pure-decision path: invoking `qrspi_resolve.py --assigned --linear-status Selected --blocked-open --blocked-by RUS-99` (no design branch) yields `entry_blocked` with `RUS-99` named in `reason`; without `--blocked-open` it yields `run_design`; an in-flight ticket (design branch present) is unaffected. All verified by the stdlib unit test suite.
**Files touched:**

- ⚠️ `scripts/qrspi_resolve_state.py` — add the `blockedOpen` branch inside the existing entry-gate `if "design" not in existing` block; fold `blockedBy` identifiers into the `entry_blocked` reason (RD4). No new function, no signature change (AC1/AC2/AC3/AC4).
- ⚠️ `scripts/qrspi_pr_state.py` — add `blocked_open=False` / `blocked_by=None` keyword params to `build_state(...)`; write `"blockedOpen"` and `"blockedBy"` into the returned dict; add matching `--blocked-open`/`--blocked-by` to the standalone CLI argparse and thread into its `build_state(...)` call.
- ⚠️ `scripts/qrspi_resolve.py` — add `--blocked-open` (`store_true`) and `--blocked-by` (repeatable/comma-joined) to argparse; forward into the `build_state(...)` call.
- ⚠️ `scripts/qrspi_resolve_state_test.py` — extend the `state(...)` factory with `blockedOpen=False` (carrying blocker identifier(s)); add a `contains`-style assertion helper (RD2); add cases: blocked+Selected → `entry_blocked` (+ each identifier substring of `reason`, RD4); unblocked+Selected → `run_design`; in-flight (design branch present) + blocked → unchanged decision.
**Verification:**
- [ ] `python3 scripts/qrspi_resolve_state_test.py` passes, including the new blocked/unblocked/in-flight cases and the `contains` reason assertion.
- [ ] `python3 scripts/qrspi_pr_state_test.py` passes (defaults keep both `build_state` callers green); a case exercises `build_state(..., blocked_open=True, blocked_by=["RUS-99"])` producing `blockedOpen=True` / `blockedBy=["RUS-99"]`.
- [ ] Manual: `python3 scripts/qrspi_resolve.py ... --assigned --linear-status Selected --blocked-open --blocked-by RUS-99` (no design branch) emits `entry_blocked` with `RUS-99` in `reason`; dropping `--blocked-open` emits `run_design`.
**Context cost:** M
**Depends on:** none

## Slice 2: Resolve-worker blocker classification (MCP read → flag reduction)

**Goal:** End-to-end against a real blocked ticket: the batch resolve worker reads `blockedBy` relations from `mcp__linear__get_issue`, classifies each blocker (open unless status type `completed`/`canceled`; unknown type → open, RD3), and appends `--blocked-open` + `--blocked-by <ids>` only when ≥1 open blocker exists — so a blocked ticket resolves to `entry_blocked` and a fully-unblocked / relation-less one to `run_design`.
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — extend resolve-prompt step 1 to read `blockedBy` relations (and any per-blocker follow-up read needed for status type — verify payload shape against live MCP, RD1); classify open unless `completed`/`canceled`, unknown → open (RD3, fail toward blocking); step 3 conditionally appends `--blocked-open` and passes ALL open blocker identifiers via `--blocked-by` (RD4). Fail-safe: append the flag ONLY on positive detection; absent/empty/unreadable relations → omit (→ `run_design`).
**Verification:**
- [ ] Manual e2e: run the batch resolve worker against a real ticket with an OPEN blocker → decision is `entry_blocked`, reason names the blocker(s).
- [ ] Manual e2e: same worker against a ticket whose blockers are all `completed`/`canceled` (or relation-less) → `--blocked-open` omitted → decision is `run_design`.
- [ ] Manual e2e (RD1): confirm whether one `get_issue` call exposes each blocker's status type or a per-blocker follow-up read is required; worker adapts without touching the Python/test surface.
**Context cost:** S
**Depends on:** Slice 1 (the `--blocked-open` / `--blocked-by` flags this slice emits must already be accepted by the script boundary).

---

## Unverified Assumptions

- **MCP payload shape (RD1, design Risk Register):** Whether a single `mcp__linear__get_issue` call returns each `blockedBy` blocker's status TYPE, or a per-blocker follow-up read is required, is NOT determinable in-repo (ref: Q5 — no fixture/schema/example payload exists). The worker must verify against the live Linear MCP during Slice 2 e2e and adapt. Does not affect the Python/test surface.
- **Status-type terminal values (design Risk Register):** The terminal "closed" set is assumed to be Linear `statusType` values exactly `completed` / `canceled`. No in-repo mapping exists (ref: Q11) — name/casing must be confirmed against live MCP in Slice 2 e2e. Any unrecognized type counts as OPEN (RD3, fail toward blocking).
- **Relation read is e2e-only:** The worker-side relation read (Slice 2) has no unit test and is verified solely by manual e2e against a real blocked ticket (ref: Q5). No automated coverage is possible in-repo for this path.
