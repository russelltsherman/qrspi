# PR: RUS-50 Respect Linear blockedBy relations at the entry gate

**Ticket:** RUS-50
**Design:** design.md @ 2026-06-08T00:00:00Z
**Structure:** structure.md @ 2026-06-09T00:00:00Z

## Summary

The autonomous QRSPI batch could start design work on a ticket whose Linear
blockers were still open. This change teaches the entry gate to honor `blockedBy`
relations: when an `assigned` + `Selected` ticket has at least one open blocker,
`resolve()` now returns `entry_blocked` (naming every open blocker in `reason`)
instead of `run_design`. The open/closed classification is reduced to a single
`--blocked-open` presence flag (plus `--blocked-by <ids>`) by the resolve worker
before the script boundary — mirroring the existing `--assigned` pattern — so the
pure resolver stays trivially unit-testable. Reviewers should focus on the
fail-safe direction (the flag is appended ONLY on positive open-blocker detection,
so absent/empty/unreadable relations proceed to `run_design`) and on the fact that
the blocker check is nested inside the `if "design" not in existing` branch, which
guarantees in-flight tickets are unaffected.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: `assigned + Selected + blockedOpen` → `entry_blocked`, reason names ALL open blockers (RD4) | `scripts/qrspi_resolve_state.py:resolve` (entry-gate `blockedOpen` branch) | `scripts/qrspi_resolve_state_test.py` blocked+Selected case + `contains(reason, id)` assertion |
| AC2: `assigned + Selected`, blockers all completed/absent → `run_design` as today | `scripts/qrspi_resolve_state.py:resolve` (falsy `blockedOpen` falls through) | `scripts/qrspi_resolve_state_test.py` unblocked+Selected case |
| AC3: in-flight ticket (design branch exists) + open blocker → decision unaffected | `scripts/qrspi_resolve_state.py:resolve` (check nested in `if "design" not in existing`) | `scripts/qrspi_resolve_state_test.py` in-flight + blocked case |
| AC4: no change to `wait`/`revise`/`reset`/`advance`/`land` paths | `scripts/qrspi_resolve_state.py:resolve` (`blockedOpen` read in one expression only) | `scripts/qrspi_resolve_state_test.py` (existing 27-case suite, all green) |
| State plumbing: `--blocked-open`/`--blocked-by` thread through `build_state` | `scripts/qrspi_pr_state.py:build_state`, `scripts/qrspi_resolve.py` argparse | `scripts/qrspi_pr_state_test.py` `build_state(..., blocked_open=True, blocked_by=["RUS-99"])` case |
| Worker classifies blockers (open unless completed/canceled; unknown → open, RD3) and emits flags | `.claude/workflows/qrspi-batch.js` resolve prompt (steps 1 & 3) | Manual e2e against live Linear MCP (no in-repo coverage — see Open Items) |

## Changes by Slice

### Slice 1: Resolver blockedOpen gate + state plumbing + tests

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_resolve_state.py` | ⚠️ modified | +9, -0 |
| `scripts/qrspi_pr_state.py` | ⚠️ modified | +11, -2 |
| `scripts/qrspi_resolve.py` | ⚠️ modified | +8, -1 |
| `scripts/qrspi_resolve_state_test.py` | ⚠️ modified | +51, -2 |
| `scripts/qrspi_pr_state_test.py` | ⚠️ modified | +36, -0 |

### Slice 2: Resolve-worker blocker classification (MCP read → flag reduction)

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | +26, -2 |

## Testing Summary

- [x] Slice 1: resolver unit tests — `python3 scripts/qrspi_resolve_state_test.py` — 27 passed, 0 failed
- [x] Slice 1: state plumbing unit tests — `python3 scripts/qrspi_pr_state_test.py` — 50 passed, 0 failed
- [x] Slice 1: manual — `qrspi_resolve.py --assigned --linear-status Selected --blocked-open --blocked-by RUS-99` (no design branch) → `entry_blocked`, reason names `RUS-99`; dropping `--blocked-open` → `run_design`; no stray worktree left behind
- [x] Slice 2: syntax — `node --check .claude/workflows/qrspi-batch.js` — OK
- [x] Slice 2: boundary regression — both Python suites re-run green (Python/test surface untouched)
- [ ] Slice 2: manual e2e against live Linear MCP (T16) — **NOT run in implementation context** (no MCP access); deferred to the batch resolve worker at runtime (see Open Items)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | | | Both slices implemented exactly as specified; impl-log records no structure deviations |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `get_issue` may not expose each blocker's status type in one call (schema unverified in-repo, RD1) | accepted / unverified — worker prompt handles both shapes (single call + per-blocker `get_issue` fallback); confirmation deferred to live-MCP e2e | Revert `.claude/workflows/qrspi-batch.js` resolve-prompt hunk |
| Relations-read failure / weak-worker misread strands a ready ticket | mitigated — flag appended ONLY on positive open-blocker detection; absent/empty/unreadable → omitted → `run_design` | Drop `--blocked-open` emission in the resolve prompt |
| New flag added to only one of two `build_state` entry points (desync) | mitigated — both `qrspi_resolve.py` and standalone `qrspi_pr_state.py` argparse updated; `qrspi_pr_state_test.py` exercises `build_state(..., blocked_open=True)` | Revert `scripts/qrspi_pr_state.py` + `scripts/qrspi_resolve.py` |
| Status-type name/casing mismatch vs. assumed `completed`/`canceled` | accepted — unrecognized types treated as OPEN (RD3, fail toward blocking); exact terminal values to be confirmed in live-MCP e2e | Adjust terminal-set comparison in resolve prompt |
| `reason` named-blocker assertion brittle if pinned to full string | mitigated — test uses `contains()` substring helper (Decision 3, Option C), not full-string equality | n/a (test-only) |

## Open Items

- **T16 manual e2e (live Linear MCP) — unverified.** The Slice 2 worker-side relation read has no in-repo automated coverage (schema unverifiable in-repo, ref Q5/RD1). Must be exercised by the batch resolve worker at runtime against: (1) a real ticket with an OPEN blocker → expect `entry_blocked` naming the blocker(s); (2) a ticket whose blockers are all `completed`/`canceled` or relation-less → expect `run_design`. This run also confirms RD1 (single `get_issue` vs. per-blocker follow-up read) and the exact terminal `statusType` values.
- **Unverified assumption — terminal status-type set** is `completed`/`canceled`. If live MCP exposes different casing/names, the worker still fails safe (unrecognized → OPEN); the e2e run should pin the exact values.
