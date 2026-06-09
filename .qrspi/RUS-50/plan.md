# Implementation Plan — qrspi resolver: respect Linear blockedBy relations at the entry gate

**Structure basis:** structure.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft
**Total steps:** 16

## Slice 1: Resolver blockedOpen gate + state plumbing + tests

### Setup

1. ⚠️ Modify `scripts/qrspi_pr_state.py` — add `blocked_open=False` and `blocked_by=None` keyword-defaulted params to `build_state(...)`, and write `"blockedOpen": blocked_open` and `"blockedBy": list(blocked_by or [])` into the returned state dict (ref: structure.md Contracts `build_state`; design §Delta).
   - **Current:** `build_state(...)` returns a dict that includes `state["assigned"]` / `state["linearStatus"]` (no blocker keys).
   - **After:** `build_state(..., blocked_open=False, blocked_by=None)` additionally writes `state["blockedOpen"] = blocked_open` and `state["blockedBy"] = list(blocked_by or [])`. Defaults keep both existing callers green.

### Core Logic

2. ⚠️ Modify `scripts/qrspi_resolve_state.py` — inside the existing `if "design" not in existing` entry-gate branch, when `state.get("assigned")` and `state.get("linearStatus") == "Selected"`, branch further on `state.get("blockedOpen")` (ref: structure.md Contracts `resolve`; design AC1/AC2/AC3/AC4).
   - **Current:** entry gate returns `run_design` iff `state.get("assigned")` truthy AND `state.get("linearStatus") == "Selected"`, else `entry_blocked` with a fixed literal `reason`.
   - **After:** same assigned + Selected check; if additionally `state.get("blockedOpen")` is truthy, return `entry_blocked` with a `reason` that folds in every identifier from `state.get("blockedBy") or []` (RD4) so each open-blocker identifier is a substring of `reason`; otherwise return `run_design` as today. No new function, no signature change.

3. ⚠️ Modify `scripts/qrspi_resolve.py` — add `--blocked-open` (`action="store_true"`) and `--blocked-by` (repeatable / comma-joined, default empty) to argparse and forward `args.blocked_open` / parsed `args.blocked_by` into the `build_state(...)` call (ref: structure.md Contracts `qrspi_resolve.py argparse`; design §Delta).
   - **Current:** argparse forwards `args.assigned` / `args.linear_status` into `build_state(...)`; no blocker flags.
   - **After:** argparse also defines `--blocked-open`/`--blocked-by`; `build_state(...)` call gains `blocked_open=args.blocked_open, blocked_by=<parsed list>`.

4. ⚠️ Modify `scripts/qrspi_pr_state.py` standalone CLI — add matching `--blocked-open` (`action="store_true"`) and `--blocked-by` (repeatable / comma-joined) to that file's own argparse and thread them into its `build_state(...)` call, keeping the two entry points in sync (ref: structure.md Contracts `qrspi_pr_state.py standalone CLI argparse`; design §Delta).
   - **Current:** standalone CLI argparse threads only `--assigned`/`--linear-status` into its `build_state(...)` call.
   - **After:** standalone CLI argparse also defines `--blocked-open`/`--blocked-by` and threads `blocked_open` / parsed `blocked_by` into its `build_state(...)` call.

### Tests

5. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — extend the `state(...)` factory with a `blockedOpen=False` parameter (carrying blocker identifier(s) into `blockedBy`) so cases can supply blocker state (ref: structure.md Contracts; design §Delta).
   - **Current:** `state(assigned, linear, phases)` factory with no blocker parameter.
   - **After:** `state(assigned, linear, phases, blockedOpen=False, blockedBy=None)` writes `blockedOpen` / `blockedBy` into the produced dict.

6. ✨ Add `contains(reason, needle) -> bool` assertion helper to `scripts/qrspi_resolve_state_test.py` — a small substring-assertion helper for verifying each open-blocker identifier appears in `reason` without pinning the full brittle string (ref: structure.md Contracts `contains` NEW test helper, RD2; design Decision 3 Option C).

7. ✨ Add resolver cases to `scripts/qrspi_resolve_state_test.py` — (a) blocked + Selected → `entry_blocked`, asserting via `contains` that each supplied open-blocker identifier is a substring of `reason` (RD4); (b) unblocked + Selected → `run_design`; (c) in-flight (design branch present) + blocked → unchanged decision (AC3) (ref: structure.md Slice 1 Verification; design §Delta).

8. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — add a case exercising `build_state(..., blocked_open=True, blocked_by=["RUS-99"])` and asserting the returned state has `blockedOpen == True` and `blockedBy == ["RUS-99"]`; confirm defaults keep existing callers green (ref: structure.md Slice 1 Verification; design Risk Register row 3).
   - **Current:** existing `build_state` test cases assert only `assigned` / `linearStatus` keys.
   - **After:** an added case asserts the `blockedOpen` / `blockedBy` keys for an explicitly-blocked call.

9. Run: `python3 scripts/qrspi_resolve_state_test.py`
   - **Expected:** all cases pass, including blocked/unblocked/in-flight cases and the `contains` reason assertion.

10. Run: `python3 scripts/qrspi_pr_state_test.py`
    - **Expected:** all cases pass; the `build_state(..., blocked_open=True, blocked_by=["RUS-99"])` case produces `blockedOpen=True` / `blockedBy=["RUS-99"]`; defaults keep existing callers green.

### Verify Slice 1

11. **Checkpoint:** `python3 scripts/qrspi_resolve_state_test.py && python3 scripts/qrspi_pr_state_test.py`
    - [ ] `qrspi_resolve_state_test.py` passes with the new blocked/unblocked/in-flight cases and `contains` reason assertion.
    - [ ] `qrspi_pr_state_test.py` passes, including the `blocked_open=True` / `blocked_by=["RUS-99"]` case.

12. **Checkpoint (manual):** `python3 scripts/qrspi_resolve.py ... --assigned --linear-status Selected --blocked-open --blocked-by RUS-99` (no design branch present)
    - [ ] Emits `entry_blocked` with `RUS-99` appearing in `reason`.
    - [ ] Dropping `--blocked-open` emits `run_design`.

---

## Slice 2: Resolve-worker blocker classification (MCP read → flag reduction)

### Core Logic

13. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — extend the resolve-prompt step 1 to read `blockedBy` relations from the `mcp__linear__get_issue` payload (and any per-blocker follow-up read needed to obtain each blocker's status type — verify payload shape against the live MCP, RD1) (ref: structure.md Slice 2 Files touched; design §Delta).
    - **Current:** resolve-prompt step 1 instructs the worker to read only the status name and whether an assignee is non-null.
    - **After:** step 1 also reads `blockedBy` relations and each blocker's status type.

14. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in the resolve prompt, classify each blocker as open unless its status type is `completed`/`canceled`, treating any unrecognized/unknown status type as open (RD3, fail toward blocking) (ref: structure.md Slice 2 Files touched; design §Delta, RD3).
    - **Current:** resolve prompt has no blocker classification logic.
    - **After:** resolve prompt classifies each `blockedBy` blocker open/closed per the terminal-set rule with unknown → open.

15. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in resolve-prompt step 3, conditionally append `--blocked-open` ONLY when at least one open blocker is positively detected, and pass the identifiers of ALL open blockers via `--blocked-by <ids>` (RD4); absent/empty/unreadable relations → omit the flag → `run_design` (fail-safe) (ref: structure.md Slice 2 Files touched; design §Delta, RD4, Risk Register row 2).
    - **Current:** resolve-prompt step 3 appends `--assigned` and substitutes `--linear-status` only.
    - **After:** step 3 also conditionally appends `--blocked-open` + `--blocked-by <open-ids>` on positive open-blocker detection, omitting both otherwise.

### Verify Slice 2

16. **Checkpoint (manual e2e):** run the batch resolve worker against real tickets.
    - [ ] Ticket with an OPEN blocker → decision is `entry_blocked`, reason names the open blocker(s).
    - [ ] Ticket whose blockers are all `completed`/`canceled` (or relation-less) → `--blocked-open` omitted → decision is `run_design`.
    - [ ] RD1: confirm whether one `get_issue` call exposes each blocker's status type or a per-blocker follow-up read is required; worker adapts without touching the Python/test surface.

---

## Rollback Notes

- No DB migrations, schema changes, or destructive operations are involved. All changes are additive over an untyped state dict and are reversible by reverting the per-file edits.
- Steps 1–8 (Python): revert via `git checkout -- <file>` per touched script; the new keys/flags are additive and default-falsy, so reverting cannot strand existing callers.
- Steps 13–15 (`.claude/workflows/qrspi-batch.js`): the resolve-prompt edits are fail-safe by construction — if reverted, the worker simply stops emitting `--blocked-open`/`--blocked-by`, which the script tolerates (flags default to absent → `run_design`). No state is persisted by these steps.
