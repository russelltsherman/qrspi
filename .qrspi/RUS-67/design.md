# Design — qrspi-batch restack aborts submit on a partially-landed stack (merged ancestors)

**Ticket:** RUS-67
**Research basis:** research.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## Current State

`qrspi_restack.py` operates purely on local branch names plus `gt`'s own behavior; it has zero merge awareness. It imports only `branch_set` and `pick_tip`, and the only external data it gathers is `git branch --list "<ticket>/*"` — no `gh` calls, no `gt`-metadata reads of tracked parents, and it never imports the existing merge classifiers (ref: Q2). `main()` computes the tip once via `pick_tip(existing_branches(...))`, which returns the highest-numbered slice and has no notion of merge status or tracked parent — the highest slice is assumed to be the open frontier regardless of whether ancestors below it have landed (ref: Q1).

The script runs four `gt` invocations: `gt checkout <tip>`, `gt restack --downstack`, a best-effort `gt abort` on conflict, and — only when a branch actually moved — `gt submit --publish --stack --force --no-edit --no-interactive`. The `--stack` submit walks the entire chain downstack from the tip (ref: Q3). The submit path is strictly conditional on `restacked == True`, which is a substring-parse of `gt`'s human output against the no-op phrase `"does not need to be restacked"`; nothing moved means the push is skipped (ref: Q8). When the lowest open slice's tracked parent is a merged branch, the script has no handling — it delegates entirely to `gt`, which aborts the non-interactive `--stack` submit because it walks into already-merged downstack branches (ref: Q9, Q10).

`classify_submit(rc, stdout, stderr)` is a pure function returning `(ok, error)`; on `rc != 0` it returns `(False, "restack succeeded but gt submit --stack failed: <detail>")` with no `gt abort` (the tree is already clean after a successful restack) (ref: Q4). The script emits a single JSON envelope on stdout — `{ ok, repoRoot, ticket, worktreeDir, tip, restacked, submitted, error? }` — and the verbatim `gt` WARNING/ERROR text is propagated only through the `error` string; there is no separate transcript log (ref: Q13). The batch calls `ensureRestacked(t)` for every queued ticket before dispatching its resolved action; any `ok:false` (conflict or submit push failure) is collapsed to `action: 'restack_conflict'` and the ticket is `continue`d — stranded before reaching its `advance`/`submit`/`land` handler (ref: Q5).

The "never `gt sync` a held stack" rule is documented in the module docstring and enforced only by omission; there is no comment anywhere about merged-ancestor pruning or the partial-land case (ref: Q6). A merged-into-trunk classifier already exists but is unused by the affected paths: `qrspi_pr_state.stack_merge_state(branches, graphql_nodes)` maps each branch to `{merged, prNumber, state, mergedByPr}` via `select_pr(prefer="merged")` ("any MERGED node wins, order-independent"), and `is_stack_fully_merged(merge_state)` is the all-or-nothing predicate — both fully unit-tested but with no consumer in restack, resolver, or batch (ref: Q9, Q10). Two distinct definitions of "merged" coexist and are reconciled nowhere: (a) GraphQL PR `merged: True`, and (b) "0 commits ahead of local trunk" via `real_branches`/`_commits_ahead` (ref: Q9).

The related resolver misreport shares the partial-land root cause but is a distinct code path. `resolve()` is pure and reads `branchExists`; the bug originates upstream in `qrspi_pr_state.build_state()`, where `branchExists = head in real` and `real_branches` keeps a branch only if `git rev-list --count main..<branch>` is `> 0`. Once an ancestor merges, the design branch's commits become reachable from trunk, its ahead-count drops to 0, `real_branches` drops it, and the resolver falls into the entry gate emitting `entry_blocked "No design branch"` even though the branch physically exists (ref: Q7).

The test convention is a pure-core / impure-shell split: `qrspi_restack_test.py` tests only the pure classifiers (`classify_result`, `classify_submit`, `build_envelope`, `worktree_path`) by passing synthetic `(rc, out, err)` tuples; the subprocess boundary is intentionally untested and verified by manual e2e (ref: Q11). The resolver test hand-builds `branchExists` booleans and has no merged-ancestor fixture; merge fixtures (`stack_merge_state` "partially-merged" case, `real_branches` regression cases) live in `qrspi_pr_state_test.py`, but no test asserts behavior for a *populated* branch reading 0-ahead because its commits landed in trunk (ref: Q12).

## Desired End State

The restack/submit path becomes merged-ancestor aware so a partially-landed stack self-advances.

- **AC: partially-landed stack restacks and re-submits the open slices, resolving to `advance`/`land` (no `restack_conflict`).** Before the `--stack` submit, the script identifies the lowest still-open slice whose tracked parent is a merged ancestor and scopes the submit so `gt` never walks into merged downstack branches; `restack()` returns `ok:true` and the batch dispatches the resolved action.
- **AC: merged ancestor branches are never included in the `gt submit --stack` call.** The submit scope is computed from a pure helper that excludes merged ancestors, so the published set is only the open slices.
- **AC: a fully-landed stack (all slices merged) short-circuits restack entirely (no checkout, no restack, no submit).** Per the reviewer's confirmation of OQ3, before any `gt` work `restack()` consults `is_stack_fully_merged(merge_state)`; when it is true the script returns `ok:true, restacked:false, submitted:false` immediately, so the batch advances to `land` without `gt` touching a fully-merged stack.
- **AC: no `gt sync` of a held stack; the fix must not disturb other tickets' branches.** The reconciliation uses a targeted re-parent / scoped submit confined to this ticket's branches; no `gt sync` and no `gt sync --delete-all` are introduced.
- **AC: stdlib-only unit tests cover the new pure logic** (which branches are merged ancestors, what the submit scope becomes), as `scripts/qrspi_*_test.py` siblings.
- **AC: manual e2e — reproduce the partial-land condition and confirm a clean batch advance**, per the verified manual workaround on RUS-40.

The related resolver fix (entry-gate misreport on a partially-landed stack) is addressed alongside, since it shares the partial-land condition: a populated phase branch whose commits have landed in trunk must still report `branchExists: true`, so the resolver no longer emits a spurious `entry_blocked "No design branch"`.

## Delta

- **Modified `scripts/qrspi_restack.py`:** Add a merge-state read (new impure shell function wrapping the existing `stack_merge_state` / a trunk-reachability probe) and a new pure helper that, given the branch set and per-branch merged flags, computes (a) the lowest open slice, (b) whether its tracked parent is a merged ancestor, and (c) the submit scope (the open-branch set). `restack()` consumes the scope to either re-parent the lowest open slice onto trunk before the existing `--stack` submit, or to issue a scoped submit covering only open branches. The `--no-op → skip push` path is preserved.
- **Fully-landed short-circuit in `restack()` (OQ3):** Before any `gt checkout`/`restack`/`submit`, `restack()` consults `is_stack_fully_merged(merge_state)` on the merge-state read above; when every branch in the stack is merged it returns `ok:true, restacked:false, submitted:false` immediately — no `gt` invocation runs against a fully-merged stack. This is the explicit fully-landed case the reviewer confirmed is in scope (distinct from the partial-land case, which still restacks the open slices).
- **New pure helper(s) in `qrspi_restack.py`:** e.g. `submit_scope(branches, merged_flags, ticket)` and `merged_ancestors(branches, merged_flags)`, both stdlib-only and tuple-in/tuple-out, matching the existing classifier style.
- **Modified `scripts/qrspi_restack_test.py`:** New cases for fully-open (no merged ancestors → full stack scope), partial-land (lower slices merged → scope = open slices only), and fully-landed (all merged → no submit) inputs to the new helpers.
- **Modified `scripts/qrspi_pr_state.py`:** Adjust `real_branches` / `branchExists` derivation so a populated branch that has landed in trunk is not conflated with an empty placeholder — distinguishing "0 ahead because empty" from "0 ahead because merged" (e.g. consult merged-PR state or local branch existence). New pure helper if the distinction is factored out.
- **Modified `scripts/qrspi_pr_state_test.py`:** New regression case for a *populated landed-ancestor* design branch asserting `branchExists: true`.
- **No changes to `qrspi-batch.js` control flow** are required if the envelope contract is unchanged; the batch already dispatches on `ok:true`.

## Pattern Decisions

### Decision 1: How to keep merged ancestors out of the `--stack` submit

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Re-parent the lowest open slice onto trunk (`gt move --onto main` / `gt track --parent main`) before the existing `gt submit --stack`, dropping merged ancestors from this ticket's stack metadata | Matches the verified RUS-40 manual workaround exactly; `--stack` then naturally lists only open slices; confined to this ticket's branches | Mutates `gt` metadata; must verify it touches only this ticket; one more impure `gt` call to wrap/classify |
| B | Scope the submit to open branches only — submit upstack from the lowest open slice instead of `--stack` from the tip | No metadata mutation; narrowest blast radius | Diverges from the proven workaround; `gt` upstack-scoping semantics must be validated; remote base chain for the lowest open slice may still point at a merged branch unless re-parented |
| C | Targeted prune of merged branches from metadata (narrower than `gt sync --delete-all`) | Cleans stale metadata directly | No proven narrow prune command; risks the shared-repo "don't disturb other tickets" constraint; closest tool is the forbidden full sync |

**Recommendation:** Option A
**Rationale:** It reproduces the verified RUS-40 repair (`gt checkout tip` → `gt restack --downstack` → `gt submit --stack` after the merged ancestors are no longer tracked), reusing the existing checkout/restack/`--stack` submit machinery unchanged (ref: Q3) and the existing `--force`/`--publish` contract. The only addition is one wrapped, classified `gt move`/`gt track` call confined to this ticket's lowest open slice — staying within the per-ticket blast radius the ticket requires.
**NEW PATTERN?** No — reuses the `_run`-wrapped `gt` invocation + pure-classifier style already established in `restack()`/`classify_result` (ref: Q3, Q11).

### Decision 2: Source of "merged ancestor" truth

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | GraphQL PR-merged via existing `stack_merge_state` / `select_pr(prefer="merged")` | Already implemented and unit-tested; authoritative "PR merged" signal | Adds a `gh` GraphQL call to a script that today makes none (ref: Q2); the two "merged" notions can disagree with local trunk (ref: Q9) |
| B | Trunk-reachability via `_commits_ahead` (0 ahead of local `main` = landed) | Same source the resolver already uses; pure-ish, no network | Conflates empty-placeholder with landed (the Q7 bug) unless paired with branch-existence; reflects only what local trunk contains |
| C | Cross-check both: a branch is a merged ancestor only when PR-merged AND below the lowest open slice | Robust against either signal's blind spot | More logic; reconciles the two notions the codebase currently leaves unreconciled |

**Recommendation:** Option A (PR-merged via `stack_merge_state`)
**Rationale:** The restack runs in a worktree whose local `main` may lag the remote (ref: Q9, "two merged notions can disagree"); the PR-merged signal is the authoritative "this ancestor has landed" fact and is already fully tested (ref: Q9, Q10). Wiring it into restack also closes the documented inconsistency that this classifier has no consumer in the affected paths.
**NEW PATTERN?** No — `stack_merge_state` is an existing tested function; this only adds its first production consumer.

### Decision 3: Fixing the resolver entry-gate misreport (related, same root cause)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | In `real_branches`/`build_state`, treat a branch that exists in git AND has a merged PR (or simply still exists locally) as present even at 0 ahead | Directly fixes the `branchExists` conflation; targeted | Must avoid re-admitting the empty-placeholder design branch the gate was built to reject (ref: Q7) |
| B | Leave the resolver untouched, fix only restack | Smaller change | Leaves the documented `entry_blocked "No design branch"` misreport live; ticket explicitly flags fixing/testing them together |

**Recommendation:** Option A
**Rationale:** The ticket calls out the resolver misreport as the same partial-land condition and asks to fix/test them together. The fix must distinguish "0 ahead because empty placeholder" from "0 ahead because the work landed in trunk" — the precise gap the `real_branches` docstring fails to acknowledge (ref: Q7, Inconsistencies).
**NEW PATTERN?** No — extends the existing `real_branches`/`_commits_ahead` gate with merged/existence awareness.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `gt move`/`gt track --parent main` mutates metadata for branches outside this ticket in the shared worktree repo | low | high | Scope the re-parent to the single lowest open slice of this ticket's branch set; verify with a dry-run (`gt submit --stack --dry-run`) that only `<ticket>/slice-*` open branches are listed before the real submit, per the RUS-40 procedure |
| The two "merged" notions disagree (PR merged but local trunk lags) causing a wrong scope | medium | medium | Use PR-merged (Decision 2A) as the authority and validate the computed scope against a `--dry-run` submit; surface a clear `error` if the dry-run set still contains a merged branch |
| Adding a `gh`/`gt`-metadata read breaks the "no merge awareness" testability split | medium | low | Keep the read in a thin impure shell; factor all decision logic into pure `submit_scope`/`merged_ancestors` helpers tested with synthetic flags (ref: Q11) |
| Resolver `real_branches` fix re-admits the empty-placeholder design branch the gate rejects | medium | medium | Gate the new "present despite 0-ahead" rule on a positive merged-PR / non-empty signal, not on bare git existence; add the populated-landed-ancestor regression test (ref: Q7, Q12) |
| `gt` human-output phrasing change silently breaks no-op detection feeding the submit trigger | low | medium | Out of scope here but noted (ref: Q8); the new scope logic does not add new phrase-parsing dependencies |

## Resolved Questions

All open questions were answered by the reviewer; the resolutions are now folded into the
design above (Decisions 1–3, the Delta, and the AC list). Recorded here for traceability:

- OQ1 → **Option A (re-parent the lowest open slice onto trunk).** Confirmed by the reviewer.
  This matches the proven RUS-40 workaround; the metadata mutation is accepted and bounded to
  this ticket's lowest open slice (see Decision 1, and the blast-radius mitigation in the Risk
  Register). No design change — this ratifies the existing recommendation.
- OQ2 → **The former: use the merged-PR signal, not bare local git existence.** Confirmed by
  the reviewer ("former"). The resolver fix (Decision 3) gates "present despite 0-ahead" on a
  positive merged-PR signal so it does not re-admit the empty-placeholder design branch the
  entry gate exists to reject. Decision 3 / its Delta and the resolver risk row are written to
  this resolution; the `gh` read in the gather is the accepted cost.
- OQ3 → **Yes — short-circuit the fully-landed case (all slices merged) via
  `is_stack_fully_merged`; no need to restack a fully-merged stack.** Confirmed by the reviewer
  ("yes no need to restack fully merged"). This is now in scope: see the new AC and the Delta /
  `restack()` short-circuit below.
- OQ4 → **Confirmed: the RUS-40 Linear projection regression (`Code Review` → `Plan Review`)
  is purely a symptom of the resolver entry-gate misreport fixed in Decision 3 — no separate
  projection fix is needed.** Once `branchExists` reports `true` for a populated landed-ancestor
  branch, the resolver stops emitting `entry_blocked` and the correct active phase (and therefore
  the correct Linear projection) follows. No additional projection-code change is in scope.
