# PR: RUS-53 Merge-aware PR selection so landed worktrees are reaped

**Ticket:** RUS-53
**Design:** design.md @ 2026-06-08T00:00:00Z
**Structure:** structure.md @ 2026-06-08T00:00:00Z

## Summary

When a branch head accrued multiple PRs (e.g. a merged PR plus a newer closed
resubmit, the RUS-30 shape), `qrspi_pr_state.py` unconditionally took the
newest-created node (`nodes[0]`) for every question, so a genuinely-landed
branch read `merged: False` and its worktree was never reaped. This change
splits the single selection chokepoint into a named primitive
`select_pr(nodes, prefer=...)`: the advancement path keeps `prefer="active"`
(identity `nodes[0]`, byte-for-byte unchanged), while the merge/land projection
in `stack_merge_state` now uses `prefer="merged"` — "any MERGED node wins",
order-independent — and the per-branch fetch cap is raised `first:5` → `first:25`.
Reviewer focus: confirm the advancement path is genuinely unchanged (the 23-case
resolver baseline is the oracle) and that the merged-preferring scan correctly
falls back to the active selection for all-open/all-closed branches.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: branch reports merged even with a newer non-merged PR | `scripts/qrspi_pr_state.py:select_pr` (`prefer="merged"`), `stack_merge_state` | `scripts/qrspi_pr_state_test.py:"merged + newer-closed: branch reads merged True"` |
| AC2: fully-landed stack (RUS-30) is reapable by cleanup + reconcile | `scripts/qrspi_pr_state.py:stack_merge_state` → `is_stack_fully_merged` | `scripts/qrspi_pr_state_test.py:"merged + newer-closed: single-branch stack is fully merged -> destroy"`; regression guard `scripts/qrspi_cleanup_test.py` (8 passed) |
| AC3: advancement reports the active PR correctly, no single-PR regression | `scripts/qrspi_pr_state.py:select_pr` (`prefer="active"`), `parse_pr_nodes` | `scripts/qrspi_pr_state_test.py:"parse_pr_nodes single-PR shape unchanged"`, `"select_pr active single-PR identity (same object)"`; oracle `scripts/qrspi_resolve_state_test.py` (23 passed) |
| AC4: multi-PR cases tested; `"picks first node"` assertion revised | `scripts/qrspi_pr_state_test.py` (new fixtures + revised assertion) | `scripts/qrspi_pr_state_test.py:"parse_pr_nodes picks active (newest) node when multiple returned"` (replaces `"picks first node when multiple returned"`) |
| AC5: deleted-head-ref sentinel no longer strands a landed branch | `scripts/qrspi_pr_state.py:stack_merge_state` (merged scan) | `scripts/qrspi_pr_state_test.py:"deleted head ref with MERGED fetched node reads merged True (AC5)"` |
| AC6: per-branch PR fetch cap raised `first:5` → `first:25` | `scripts/qrspi_pr_state.py:PR_QUERY` | covered by `scripts/qrspi_pr_state_test.py` order-independent fixtures (selection robust within window); cap value is a query-string constant |

## Changes by Slice

### Slice 1: Merge-aware PR selection at the single chokepoint

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_pr_state.py` | modified | +52, -11 |
| `scripts/qrspi_pr_state_test.py` | modified | +118, -8 |

Changes: added `select_pr(nodes, prefer)` primitive; re-expressed `parse_pr_nodes`
over `prefer="active"` (rename, no behavior change); sourced `stack_merge_state`
per-branch `merged`/`prNumber`/`state` from `prefer="merged"`; added additive
`mergedByPr` observability key; raised `PR_QUERY` cap to `first:25`.

### Phase artifacts (not code)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-53/questions.md` | new | +49 |
| `.qrspi/RUS-53/research.md` | new | +330 |
| `.qrspi/RUS-53/design.md` | new | +82 |
| `.qrspi/RUS-53/structure.md` | new | +103 |
| `.qrspi/RUS-53/plan.md` | new | +125 |
| `.qrspi/RUS-53/worktree.md` | new | +35 |
| `.qrspi/RUS-53/impl-log.md` | new | +42 |

## Testing Summary

- [x] Slice 1: unit tests — `python3 scripts/qrspi_pr_state_test.py` — 46 passed, 0 failed
- [x] Advancement regression oracle — `python3 scripts/qrspi_resolve_state_test.py` — 23 passed, 0 failed (byte-for-byte baseline unchanged; design refers to it as 24, the file has 23 — count label was imprecise, behavior is unchanged)
- [x] Downstream cleanup consumer — `python3 scripts/qrspi_cleanup_test.py` — 8 passed, 0 failed (consumes `stack_merge_state`/`is_stack_fully_merged`, green without modification)
- [x] RUS-30 path verified in-test: merged + newer-closed branch yields `is_stack_fully_merged == True` (→ cleanup `destroy`, not `skip`)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| (none) | structure.md contracts implemented as specified | `select_pr`, `parse_pr_nodes`, `stack_merge_state`, `is_stack_fully_merged` match the outline; optional `mergedByPr` key was added per Design Delta §1 | No deviations. The optional observability key was exercised. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `"picks first node when multiple returned"` test fails after the fix, blocking CI | Mitigated — assertion replaced by `"parse_pr_nodes picks active (newest) node when multiple returned"` (AC4) | Revert `scripts/qrspi_pr_state_test.py` |
| Advancement path regresses if the split changes `parse_pr_nodes` | Mitigated — change confined to `stack_merge_state`'s projection; `parse_pr_nodes` reduces to identity for single-PR; 23-case resolver baseline green | Revert `scripts/qrspi_pr_state.py` |
| A MERGED PR beyond the fetch cap is invisible | Mitigated — cap raised `first:5` → `first:25` (AC6) | Lower `first:25` back to `first:5` in `PR_QUERY` |
| Deleted-head-ref sentinel forces `merged: False` for a landed branch | Resolved — "any MERGED node wins" scan returns `merged: True` (AC5), test added | Revert `stack_merge_state` to sentinel-only path |
| Merge scan marks a branch merged from an unrelated stale MERGED PR on the same head ref | Accepted — one head ref per branch in this harness; fixtures are same-branch only | N/A (accepted risk) |

## Open Items

- `mergedByPr` is purely additive observability; no consumer reads it today. A
  follow-up could surface it in `qrspi_cleanup.py`'s `reason` string so an
  operator can see which PR drove the merged verdict (design Q13).
- No `isDraft`/DRAFT handling was added — out of scope for this ticket
  (design §Current State notes it is neither queried nor carried).
