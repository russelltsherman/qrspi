# Design — Wrong PR chosen when a branch has multiple PRs, stranding merged worktrees

**Ticket:** RUS-53
**Research basis:** research.md @ 2026-06-08T00:00:00Z
**Generated:** 2026-06-08T00:00:00Z
**Status:** draft

## Current State

The harness fetches up to 5 PRs per branch head via `PR_QUERY` (`scripts/qrspi_pr_state.py`), ordered server-side by `CREATED_AT DESC`, but `parse_pr_nodes` unconditionally takes `nodes[0]` — the newest-created PR — and discards the rest (ref: Q1). This collapse is a pure sort-then-take-first: a server-side creation-time sort plus a client-side list-index `[0]`, with no filter on state and no preference for a MERGED PR (ref: Q3). The query's `first:5` multi-PR capacity is effectively dead — fetched but never used beyond index 0 (ref: Q1).

The normalized PR shape carries `prExists`, `number`, `reviewDecision`, `unresolvedThreads`, `merged` (bool), `state` (OPEN/CLOSED/MERGED), and `mergedAt`; `closedAt`, `createdAt`, `updatedAt`, and `isDraft` are neither queried nor carried (ref: Q2). Of the carried fields, only `state`, `merged`, `mergedAt`, and `number` could disambiguate competing PRs, but disambiguation never happens because the collapse to `nodes[0]` precedes any consumer (ref: Q2).

Two distinct questions consume this single lossy PR. The advancement question is answered by `qrspi_resolve_state.resolve(state)`, reading `prExists`/`reviewDecision`/`unresolvedThreads` per phase and slice (ref: Q4). The merge/land question is answered by `is_stack_fully_merged(merge_state)` and `classify_cleanup`, reading the `merged` bool from `stack_merge_state` (ref: Q4, Q6). Both derive their per-branch PR from `parse_pr_nodes`, so both inherit the newest-created-wins collapse; they read disjoint field subsets but share one lossy source (ref: Q4). `is_stack_fully_merged` is all-or-nothing: every real branch entry must have `merged == True`, and an empty stack or deleted-head-ref sentinel reads `merged: False` (ref: Q6, Q11).

The reconcile sweep in `qrspi-batch.js` invokes the identical `python3 scripts/qrspi_cleanup.py --ticket <id>` command as the post-land reap, so both routes run the same `classify_cleanup` → `stack_merge_state` → `parse_pr_nodes` chain and inherit the same wrong answer (ref: Q7). The RUS-30 case — a merged PR plus a newer closed (non-merged) PR on the same branch — returns the newer CLOSED PR's state (`merged: False`), so cleanup reads `skip` and the landed worktree is stranded (ref: Q8). The inverse case (earlier closed, later merged) happens to resolve correctly only because the merged PR is newest-created (ref: Q9). There is no DRAFT handling anywhere — `isDraft` is never queried (ref: Q11).

Observability is minimal: `parse_pr_nodes` logs neither which node it picked nor how many it discarded; cleanup's `reason` is a fixed string that never names the driving PR. An operator cannot see "branch X had #100(closed) and #99(merged); chose #100" from any current output (ref: Q13).

The single-PR case is the backward-compat baseline: with one node, `nodes[0]` IS that node, so any correct fix must reduce to identity when `len(nodes) == 1` (ref: Q10). Test fixtures overwhelmingly assume one PR per branch; the only multi-PR test, `"picks first node when multiple returned"`, pins the buggy index-0 behavior as correct and would fail a correct fix (ref: Q12).

## Desired End State

- **AC1** — A branch whose work has merged is reported as merged even when a newer non-merged PR also exists. Achieved by replacing the newest-created-wins collapse for the merge question with a merged-preferring selection: if any of the (up to 5) fetched PRs is MERGED, the branch's merge signal is `merged: True` (ref: Q3, Q8).
- **AC2** — A fully-landed stack with such a branch (RUS-30) is identified as reapable by both cleanup and reconcile. Because both routes funnel through the same selection chokepoint, fixing `parse_pr_nodes` / the merge projection fixes both simultaneously: `stack_merge_state` reports `merged: True` for the branch → `is_stack_fully_merged` → `destroy` (ref: Q6, Q7).
- **AC3** — The advancement path reports the active PR correctly when multiple PRs exist, with no single-PR regression. The advancement question keeps selecting the active (open/most-recent reviewable) PR, distinct from the merge question's merged-preferring selection (ref: Q4, Q10).
- **AC4** — Multi-PR cases are covered by tests: merged + later closed, closed + later merged, and the single-PR identity case; the `"picks first node"` assertion is revised (ref: Q12).
- **AC5** — The deleted-head-ref sentinel no longer strands a genuinely-landed branch: when a branch's head ref is gone but one of its fetched PRs is MERGED, the merge signal is `merged: True` (folds the sentinel case into the same merged-preferring scan as AC1, rather than deferring it; resolves former OQ1, ref: Q6, Q11).
- **AC6** — The per-branch PR fetch cap is raised from `first:5` to `first:25`, so a branch that accrued many resubmits (closed PRs) before its merge still surfaces the MERGED node within the fetch window (resolves former OQ2, ref: Q1).

## Delta

- **Modified `scripts/qrspi_pr_state.py`** — Split the single-collapse chokepoint so the two questions get the PR each needs. Introduce a merge-aware selector for the cleanup projection (`stack_merge_state`) that scans all fetched nodes and reports `merged: True` if any node is MERGED, rather than reading `nodes[0]["merged"]`. Intent-name the advancement-facing selection (the `parse_pr_nodes`/resolver path) as the **active PR** (`prefer="active"`), preserving its current single-PR/common-case behavior byte-for-byte (reduces to identity when `len(nodes) == 1`, ref: Q10, OQ3) — a rename, not a behavior change. Optionally extend the projected shape so the cleanup envelope records which PR number drove the merged verdict (observability, ref: Q13).
- **Modified `scripts/qrspi_pr_state_test.py`** — Add fixtures for merged + newer-closed, closed + newer-merged, and single-PR identity; revise/replace the `"picks first node when multiple returned"` assertion to reflect the corrected selection (ref: Q12).
- **Possibly modified `scripts/qrspi_resolve_state_test.py`** — Only if the advancement selection changes; if advancement keeps `nodes[0]` semantics this file is untouched (preserving the 24-case byte-for-byte baseline, ref: Q10).
- **Modified `PR_QUERY` in `scripts/qrspi_pr_state.py`** — Raise the per-branch PR fetch cap from `first:5` to `first:25` so the merged-preferring scan sees the MERGED node even on a branch with many prior resubmits (former OQ2, now AC6). No new fields are required (`state`/`merged` are already per-node); `createdAt` is still not added because the merge selection is order-independent (see Decision 2).
- **Merge scan also fixes the deleted-head-ref sentinel (AC5)** — folding the sentinel into the same "any MERGED node wins" scan means a landed branch whose head ref was deleted reads `merged: True` whenever any fetched PR is MERGED, rather than falling back to the `merged: False` sentinel. This is in scope because it is the same selection chokepoint, not a new code path (former OQ1).
- **No PR-write operations anywhere** (constraint).

## Pattern Decisions

### Decision 1: Where to split the merge question from the advancement question

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add a merge-aware projection inside `stack_merge_state` that scans all nodes for any MERGED; leave `parse_pr_nodes` (advancement) at `nodes[0]` | Surgical; advancement path byte-for-byte unchanged (AC3/Q10); honors additive-field discipline (ref: Discovered Patterns); both questions already consume disjoint fields (ref: Q4) | Two selection rules now live in one module; reader must know which question uses which |
| B | Make `parse_pr_nodes` return the full candidate list and push all selection into each caller | Maximum flexibility; selection criterion explicit per consumer | Breaks the shape every resolver caller depends on; large blast radius; violates backward-compat baseline (ref: Q10) |
| C | Add a generic `select_pr(nodes, prefer=...)` helper, call with `prefer="merged"` for cleanup and `prefer="active"` for advancement | One named, testable selection primitive; intent-explicit per the ticket goal | Slightly more surface than A; must prove the `prefer="active"` path reduces to identity for single-PR (ref: Q10) |

**Recommendation:** Option A for the merge-question fix, with the advancement side intent-named per Option C (`prefer="active"`) — see Resolved Question OQ3. 
**Rationale:** The research identifies a single collapse chokepoint that both questions inherit (ref: Q3, Discovered Patterns), and the two questions already read disjoint field subsets from a shared source (ref: Q4). Fixing the merge projection in `stack_merge_state` (Option A) leaves the advancement *behavior* and its 24 pinned tests untouched (ref: Q10), directly satisfying AC3's no-regression clause while the merge scan satisfies AC1/AC2. Per OQ3 the advancement selection is additionally given an explicit intent name (`select_pr(nodes, prefer="active")` reducing to identity for the single-PR case) so the two questions read legibly side by side — a rename, not a behavior change. This matches the additive-field discipline already established in the module (ref: Discovered Patterns).
**NEW PATTERN?** No — extends the existing pure-core selection function in the same module the codebase already uses for per-branch PR normalization.

### Decision 2: Selection rule for the merge question

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | "Any MERGED node wins" — branch is merged if any of the fetched PRs has `merged == True` | Directly models "did this branch's work land?"; order-independent; needs only existing `merged` field (ref: Q2); correct for both RUS-30 and its inverse (ref: Q8, Q9) | A stale merged PR from an unrelated re-push could in theory mark a branch merged — low risk given one head ref per branch |
| B | Sort by `createdAt` then prefer MERGED — add `createdAt` to query, tiebreak by recency among merged | Most precise ordering | Requires querying a field not currently carried (ref: Q2); more surface; recency is irrelevant to "did it land" |
| C | Prefer `state == MERGED`, else fall back to `nodes[0]` | Simple precedence rule | Functionally equivalent to A for the merge bool; extra branching with no added correctness |

**Recommendation:** Option A. 
**Rationale:** The merge/land question asks only "did this branch's work land," for which recency is irrelevant — the documented divergence is precisely that "latest-created ≠ authoritative/merged" (ref: Inconsistencies, Q9). "Any MERGED wins" uses only the already-carried `merged`/`state` fields (ref: Q2), needs no new query field, and is order-independent, so it is robust to either creation order (ref: Q8, Q9). To keep the scan robust against a branch that accrued many resubmits before merging, the fetch cap is raised to `first:25` (AC6) so the MERGED node is within the window. The all-or-nothing stack semantic is preserved — only the per-branch signal becomes correct (ref: Q6).
**NEW PATTERN?** Yes (mild) — introduces the codebase's first selection key other than creation order (ref: Discovered Patterns: "Creation-time is the only ordering key in play"). Justified because the merge question's intent (landed-ness) is semantically a state predicate, not a recency pick; existing recency-only ordering cannot express it.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| The `"picks first node when multiple returned"` test fails after the fix, blocking CI | High | Low | Expected — revise that assertion as part of AC4; it currently pins the bug (ref: Q12, Inconsistencies) |
| Advancement path regresses if the split accidentally changes `parse_pr_nodes` | Medium | High | Confine the change to `stack_merge_state`'s projection; keep `parse_pr_nodes` single-node behavior identical; lean on the 24 pinned resolver tests as the oracle (ref: Q10) |
| A MERGED PR beyond the fetch cap is invisible, so a truly-landed branch still reads unmerged | Low | Low | Cap raised from `first:5` to `first:25` (AC6); a branch realistically accrues only a handful of resubmits, so the MERGED node is now well within the window (ref: Q1) |
| Deleted-head-ref sentinel forces `merged: False` even when the branch genuinely landed | Medium | Medium | Resolved here (AC5): the "any MERGED node wins" scan returns `merged: True` whenever a fetched PR is MERGED, so a deleted-head-ref branch with a MERGED PR is no longer stranded — same chokepoint, no new code path (ref: Q6, Q11) |
| Merge-aware scan marks a branch merged from an unrelated stale MERGED PR on the same head ref | Low | Medium | Acceptable given one head ref per branch in this harness; tests should include only same-branch fixtures (ref: Q8) |

## Resolved Questions

These were raised during design and are now resolved (per reviewer feedback) — folded into the ACs/Delta above so nothing is left open:

- **OQ1 — deleted-head-ref sentinel: address it here.** The sentinel (which reads `merged: False` even for a genuinely-landed branch, ref: Q6, Q11) is fixed in this design, not deferred. It is the same selection chokepoint as the multi-PR bug — the "any MERGED node wins" scan returns `merged: True` whenever a fetched PR is MERGED — so resolving it adds no new code path. Codified as **AC5** and in the Delta ("Merge scan also fixes the deleted-head-ref sentinel").
- **OQ2 — raising `first:5` is warranted.** The fetch cap is raised to `first:25` so a branch that accrued many resubmits (closed PRs) before its merge still surfaces the MERGED node within the order-independent scan window. The cost is one larger GraphQL page; the benefit is removing a silent failure mode for the merged-preferring scan. Codified as **AC6** and in the Delta ("Modified `PR_QUERY`").
- **OQ3 — the advancement question becomes intent-named.** Rather than leaving advancement as an implicit `nodes[0]`, name its selection intent explicitly as the **active PR** (Decision 1 Option C's `select_pr(nodes, prefer="active")` framing) so the two questions — merge-preferring vs. active — are legible side by side. The selection *behavior* for the single-PR/common case is unchanged (it must reduce to identity when `len(nodes) == 1`, ref: Q10), preserving the 24 pinned resolver tests; only the naming/intent becomes explicit. This is editability/clarity, not a correctness change, and stays within the merge-question chokepoint plus a thin rename on the advancement side.
