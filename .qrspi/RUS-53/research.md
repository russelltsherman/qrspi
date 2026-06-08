# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-08T00:00:00Z
**Generated:** 2026-06-08T00:00:00Z
**Status:** draft

## Q1: How does the code gather the set of PRs associated with a single branch, and does it request all PRs for a branch head or only the first/latest one returned by the gh GraphQL query?

**Answer:** The GraphQL query (`PR_QUERY`) requests up to 5 PRs for a head ref, ordered by `CREATED_AT DESC` (newest first). The full node list is returned by `_query_pr`, but `parse_pr_nodes` then **unconditionally takes `nodes[0]`** — i.e. the single most-recently-created PR — and discards the rest. So while the query *fetches* multiple PRs, every downstream consumer of `parse_pr_nodes` (the OPEN-path resolver gather and the merge-state gather) sees only the newest-created PR for that branch. The query is the only place all PRs are visible; the collapse to one happens immediately at parse time.

**Evidence:**

```
pullRequests(headRefName:$head, first:5, orderBy:{field:CREATED_AT, direction:DESC}) {
  nodes { number state merged mergedAt reviewDecision reviewThreads(first:100) { nodes { isResolved } } }
}
```

— `scripts/qrspi_pr_state.py:26-41`

```
    if not nodes:
        return {"prExists": False, ...}
    node = nodes[0]
```

— `scripts/qrspi_pr_state.py:62-66`

**Dependencies:** `_query_pr` (subprocess `gh api graphql`) → `parse_pr_nodes` → consumed by `build_state` (resolver path) and `stack_merge_state` (cleanup path). Upstream: `gh` CLI GraphQL. Downstream: `qrspi_resolve_state.resolve`, `qrspi_cleanup.classify_cleanup`.
**Implicit contracts:** Callers assume "the PR for this branch" is a single object. The `orderBy: CREATED_AT DESC` + `nodes[0]` pairing encodes "newest-created PR wins" — never "merged PR wins" or "by PR number". `first:5` caps visibility at 5 PRs; a 6th would never be seen even by the query.

## Q2: What fields (state, mergedAt, closedAt, createdAt, updatedAt, number, isDraft) are carried per PR from the gather step into the resolver, and which of these are currently available to disambiguate multiple PRs on one branch?

**Answer:** The normalized PR shape carries exactly: `prExists`, `number`, `reviewDecision`, `unresolvedThreads`, `merged` (bool), `state` (str: OPEN/CLOSED/MERGED), `mergedAt`. `branchExists`/`n` are added later for phase/slice entries. **`closedAt`, `createdAt`, `updatedAt`, and `isDraft` are NOT queried and NOT carried** — they are unavailable downstream. Of the carried fields, only `state`, `merged`, `mergedAt`, and `number` could disambiguate multiple PRs, but disambiguation never happens because `parse_pr_nodes` already collapsed to `nodes[0]`. The merge fields are documented as ADDITIVE (existing OPEN-path callers read only `prExists`/`number`/`reviewDecision`/`unresolvedThreads`).

**Evidence:**

```
    return {
        "prExists": True, "number": node.get("number"),
        "reviewDecision": node.get("reviewDecision"),
        "unresolvedThreads": unresolved_thread_count(threads),
        "merged": bool(node.get("merged")),
        "state": node.get("state"), "mergedAt": node.get("mergedAt"),
    }
```

— `scripts/qrspi_pr_state.py:68-76`

**Dependencies:** Fields flow into the `state` envelope's `phases.{design,plan}` (full PR shape) and `phases.implementation.slices[]` (PR shape + `n`). `stack_merge_state` projects to `{merged, prNumber, state}` only.
**Implicit contracts:** The envelope schema is the contract between `qrspi_pr_state` and both `qrspi_resolve_state` and `qrspi_cleanup`. Any disambiguation by creation time would require querying `createdAt` (currently absent) — only `CREATED_AT` *sort order* is used, never the timestamp value itself. Distinguishing merged-vs-closed needs `state`/`merged`, which ARE present per-node but only for `nodes[0]`.

## Q3: Where in the data path does a branch's many PRs collapse into the single "the PR for this branch" value, and is that collapse a list-index, a filter, or a sort-then-take-first?

**Answer:** The collapse is a **sort-then-take-first**: the sort is done server-side by GitHub (`orderBy:{field:CREATED_AT, direction:DESC}` in `PR_QUERY`), and the take-first is `node = nodes[0]` in `parse_pr_nodes`. There is no filter on state, no preference for MERGED, no scan of the list. It is a pure list-index `[0]` over a creation-time-descending list. Every consumer inherits this single collapse point.

**Evidence:**

```
def parse_pr_nodes(nodes):
    if not nodes:
        return {"prExists": False, ...}
    node = nodes[0]
```

— `scripts/qrspi_pr_state.py:52-66`

A unit test explicitly pins the current behavior:

```
check("picks first node when multiple returned",
      parse_pr_nodes([{"number": 100, ...}, {"number": 99, ...}])["number"], 100)
```

— `scripts/qrspi_pr_state_test.py:76-81`

**Dependencies:** Single chokepoint: `parse_pr_nodes`. Both the resolver path (`build_state` → `phase_pr`/slice loop) and the cleanup path (`stack_merge_state`) route through it.
**Implicit contracts:** "Representative PR = newest created." A newer CLOSED (non-merged) re-open of a branch outranks an older MERGED PR. This is the suspected root cause of the wrong-PR selection: a sort key of creation time, not merge status.

## Q4: What is the current function/return-value contract for the "did this branch land?" merge/cleanup question versus the "what is this branch's active PR doing?" review/advancement question — are they two separate functions or one shared lookup?

**Answer:** They are **two separate functions that share the same single-PR lookup** (`parse_pr_nodes`). (1) The advancement question is answered by `qrspi_resolve_state.resolve(state)`, which reads `prExists`/`reviewDecision`/`unresolvedThreads` per phase and per slice via predicates `_pr_ready`, `_pr_changes_requested`. (2) The merge/land "did it land?" question is answered by `is_stack_fully_merged(merge_state)` (and `classify_cleanup`), which reads the `merged` bool produced by `stack_merge_state`. Both derive their per-branch PR from `parse_pr_nodes` (`nodes[0]`), so both inherit the same newest-created-wins collapse.

**Evidence:**

```
def _pr_ready(pr):
    return pr.get("reviewDecision") == "APPROVED" and pr.get("unresolvedThreads", 0) == 0
```

— `scripts/qrspi_resolve_state.py:65-66`

```
def is_stack_fully_merged(merge_state):
    if not merge_state: return False
    return all(entry.get("merged") for entry in merge_state.values())
```

— `scripts/qrspi_pr_state.py:107-114`

**Dependencies:** Advancement: `resolve` (pure, no I/O). Land/cleanup: `is_stack_fully_merged` + `classify_cleanup`. Both upstream of `parse_pr_nodes`.
**Implicit contracts:** `resolve` never reads `merged`/`state`/`mergedAt`; the cleanup path never reads `reviewDecision`/`unresolvedThreads`. The two questions use disjoint field subsets but a shared (and currently lossy) source PR.

## Q5: What inputs does scripts/qrspi_resolve.py pass through from the gather step to the resolver and to artifact/cleanup detection, and which callers (orchestrator, batch) consume the branch-state result?

**Answer:** `qrspi_resolve.py:main` calls `build_state(owner, repo, ticket, assigned, linear_status, trunk)` (the full gather) → feeds its returned `state` dict straight into `resolve(state)` → then provisions the worktree (only if `decision["action"] == "run_design"`) → then `detect_existing(<worktree>/.qrspi/<ticket>)` for artifact presence. It assembles a single envelope `{ok, repoRoot, worktreeDir, existing, decision, reviewers, teamReviewers, ticketContent}`. **Notably `qrspi_resolve.py` does NOT call any cleanup/merge-state path** — reaping is a separate script (`qrspi_cleanup.py`) invoked from the batch workflow, not from the resolve envelope. The consumer is the `qrspi-batch.js` workflow (the `resolveTicket()` step) and the `qrspi-work` SKILL.

**Evidence:**

```
state = build_state(owner, repo, args.ticket, args.assigned, args.linear_status, trunk=args.trunk)
decision = resolve(state)
worktree = setup_worktree(args.ticket, trunk=args.trunk, create_design=(decision["action"]=="run_design"))
existing = detect_existing(os.path.join(worktree, ".qrspi", args.ticket))
```

— `scripts/qrspi_resolve.py:328-333`

**Dependencies:** `build_state` (gh+git) → `resolve` (pure). Envelope consumed by `.claude/workflows/qrspi-batch.js` and `.claude/skills/qrspi-work/SKILL.md`. Cleanup is wired separately (Q6/Q7).
**Implicit contracts:** Envelope shape is documented at `scripts/qrspi_resolve.py:27-28` and `build_envelope` (`:177-203`). The resolve path is read-only for non-`run_design` actions (`setup_worktree` creates nothing unless `create_design`). Merge/cleanup state is intentionally NOT in this envelope.

## Q6: How is a stack determined to be "fully merged" / reapable today, and which per-branch merge signal does that determination read?

**Answer:** Reap eligibility is decided by `classify_cleanup(stack_merge_state, dirty_porcelain)` in `qrspi_cleanup.py`, which returns `blocked` (dirty worktree, takes precedence), `destroy` (stack fully merged), or `skip` (anything else). "Fully merged" = `is_stack_fully_merged(merge_state)` = **every** real branch entry has `merged == True` (all-or-nothing; empty stack → False). The per-branch merge signal is the `merged` boolean from `stack_merge_state`, which comes from `parse_pr_nodes(nodes)["merged"]` = `bool(nodes[0].merged)` — i.e. the GraphQL `merged` field of the **newest-created** PR on that head ref.

**Evidence:**

```
    if (dirty_porcelain or "").strip():
        return {"decision": "blocked", ...}
    if is_stack_fully_merged(stack_merge_state):
        return {"decision": "destroy", "reason": "stack fully merged"}
    return {"decision": "skip", "reason": "stack not fully merged"}
```

— `scripts/qrspi_cleanup.py:75-88`

```
        pr = parse_pr_nodes(nodes)
        out[b] = {"merged": pr["merged"], "prNumber": pr["number"], "state": pr["state"]}
```

— `scripts/qrspi_pr_state.py:98-103`

**Dependencies:** `classify_cleanup` ← `is_stack_fully_merged` ← `stack_merge_state` ← `parse_pr_nodes` ← `_query_pr`. Invoked by `qrspi_cleanup.run` → from `qrspi-batch.js` (`reapTicket`/post-land cleanup at `:647`, `:717-768`).
**Implicit contracts:** The reap signal is the newest PR's `merged` bool. If a branch's newest-created PR is a CLOSED-unmerged re-open while its real landing PR is an older MERGED one, `merged` reads `False` → `is_stack_fully_merged` → `skip` → the merged worktree is stranded (the symptom). A branch with a deleted head ref (post-merge) maps to the sentinel `{merged: False, ...}` (`scripts/qrspi_pr_state.py:96`), which ALSO blocks reaping.

## Q7: How does the reconcile sweep recompute branch state, and does it call the same selection logic as the primary cleanup path (such that both inherit the same wrong answer)?

**Answer:** Yes — they are the same code path. The reconcile sweep (`reconcileCandidates()` / the reconciliation loop in `qrspi-batch.js`, RUS-52) enumerates candidate stranded tickets, then for each invokes the **identical** `python3 scripts/qrspi_cleanup.py --ticket <id>` command used by the post-land cleanup. Both routes run `qrspi_cleanup.run` → `classify_cleanup` → `stack_merge_state` → `parse_pr_nodes`. There is no separate selection logic in the sweep; it inherits the same newest-created-wins collapse and therefore the same wrong answer.

**Evidence:**

```
// CLEANUP — deterministic post-merge reap (RUS-52). ...verbatim invocation of
// the self-locating, tested qrspi_cleanup.py.
  python3 scripts/qrspi_cleanup.py --ticket ${ticketId}${dryFlag}
```

— `.claude/workflows/qrspi-batch.js:630-647`

```
async function reconcileCandidates() { ... }
// sweep loop:  const cl = await ... cleanupTicket(id, dryRun) ...
```

— `.claude/workflows/qrspi-batch.js:717-768`

**Dependencies:** Both `reapTicket` (post-land, `:663-681`) and the reconcile sweep (`:741-768`) call the same `cleanup` worker invoking `qrspi_cleanup.py`. Single shared script.
**Implicit contracts:** `--dry-run` gates only execution, not the decision (`scripts/qrspi_cleanup.py:22-23, 212`), so the dry-run preview shown by reconcile is a faithful mirror of the live reap — and of the same selection bug.

## Q8: For a branch with a merged PR plus a newer closed (non-merged) PR — the RUS-30 case — what value does the current selection return, and which PR's state wins?

**Answer:** The **newer CLOSED (non-merged) PR wins**. Because `PR_QUERY` sorts `CREATED_AT DESC` and `parse_pr_nodes` takes `nodes[0]`, the newest-created PR is selected. A closed-but-not-merged PR created after the merged one returns `{merged: False, state: "CLOSED", ...}`. `resolve` (advancement) would see no APPROVED/merged signal; `classify_cleanup` (cleanup) sees `merged == False` → `is_stack_fully_merged` → `skip` → the actually-landed worktree is never reaped (RUS-30 stranding). The older MERGED PR is fetched by the query (within `first:5`) but discarded at index 0.

**Evidence:**

```
    node = nodes[0]
    return { ... "merged": bool(node.get("merged")), "state": node.get("state"), ... }
```

— `scripts/qrspi_pr_state.py:66-76`

Current pinned behavior (newest-by-query-order wins regardless of state):

```
check("picks first node when multiple returned", parse_pr_nodes([{"number":100,...},{"number":99,...}])["number"], 100)
```

— `scripts/qrspi_pr_state_test.py:76-81`

**Dependencies:** `parse_pr_nodes` → both `merged` (cleanup) and `reviewDecision` (resolver). The wrong PR poisons both questions.
**Implicit contracts:** No code anywhere prefers `merged == True` over a newer non-merged PR. Disambiguation by state is absent. This is the documented RUS-30 failure mode.

## Q9: For a branch with an earlier closed PR followed by a later merged PR, how does the current selection order them, and does ordering rely on PR number, creation time, or array position?

**Answer:** Ordering relies on **creation time** (server-side `orderBy:{field:CREATED_AT, direction:DESC}`), then **array position** (`nodes[0]`). PR number is NOT used as a sort key. For an earlier-closed + later-merged branch, the later MERGED PR is `nodes[0]` and wins — so this ordering happens to produce the correct answer (merged) here. The bug only manifests when the *newest-created* PR is the non-merged one (Q8). Note the ordering is purely creation-time; `number` is carried as data but never used to order or select.

**Evidence:**

```
pullRequests(headRefName:$head, first:5, orderBy:{field:CREATED_AT, direction:DESC})
```

— `scripts/qrspi_pr_state.py:29`

```
node = nodes[0]
```

— `scripts/qrspi_pr_state.py:66`

**Dependencies:** GitHub server-side sort + `parse_pr_nodes[0]`. No client-side sort exists.
**Implicit contracts:** "Newest created = representative." Correctness is incidental whenever the latest-created PR also happens to be the merged/authoritative one; it breaks precisely when those diverge (a re-opened/duplicate PR created after the real landing PR).

## Q10: How is the common single-PR-per-branch case currently resolved, so that any multi-PR fix can be verified to leave it byte-for-byte unchanged (the backward-compatibility constraint)?

**Answer:** With exactly one PR node, `nodes[0]` is that PR, so `parse_pr_nodes` returns its full normalized shape; with zero nodes it returns the `prExists: False` sentinel. `resolve` then walks its decision ladder per phase: entry gate → reset/revise (CHANGES_REQUESTED) → submit (branch exists, no PR) → wait (threads, or not APPROVED) → advance (APPROVED+clean) → land (all slices APPROVED+clean). For the single-PR case the multi-PR collapse is a no-op (`nodes[0]` IS the only PR), so any fix that preserves single-node behavior keeps this byte-for-byte. The contract is fully pinned by `qrspi_resolve_state_test.py` (all fixtures use a single PR object per phase) and the single-node `parse_pr_nodes` tests.

**Evidence:**

```
def _phase(branch=True, pr=True, decision="REVIEW_REQUIRED", threads=0):
    return {"branchExists": branch, "prExists": pr, "reviewDecision": decision, "unresolvedThreads": threads}
```

— `scripts/qrspi_resolve_state_test.py:14-16`

```
if not pr.get("prExists"): return decision("submit", ...)
...
if pr.get("reviewDecision") != "APPROVED": return decision("wait", ...)
return decision("advance", ...)
```

— `scripts/qrspi_resolve_state.py:131-150`

**Dependencies:** `resolve` decision ladder; `parse_pr_nodes` single-node path. Tests at `qrspi_resolve_state_test.py` (24 cases) and `qrspi_pr_state_test.py`.
**Implicit contracts:** Backward-compat baseline = "one node in, that node's shape out." A correct multi-PR fix must reduce to identity when `len(nodes) == 1`. The existing `parse_pr_nodes([single])` tests (`:49-66`) are the byte-for-byte oracle.

## Q11: How does the existing logic treat a branch with zero PRs, or PRs in OPEN/DRAFT state alongside a MERGED one, in both the merge question and the advancement question?

**Answer:** Zero PRs → `parse_pr_nodes([])` returns `{prExists: False, merged: False, state: None, ...}`. Advancement: `prExists == False` on an existing branch → `submit` (`resolve` `:131-132`). Merge/cleanup: `merged == False` → contributes to NOT-fully-merged → `skip` (and the deleted-head-ref sentinel at `:96` likewise reads `merged: False`). For OPEN/DRAFT alongside MERGED: there is **no DRAFT handling at all** (`isDraft` is never queried). State is decided solely by `nodes[0]`. If the OPEN/DRAFT PR is newer-created, it wins → `merged: False` → cleanup skips and advancement sees it un-approved; if the MERGED PR is newer-created, it wins. So the answer depends entirely on creation order, never on a MERGED-preferring rule.

**Evidence:**

```
if not nodes:
    return {"prExists": False, "number": None, "reviewDecision": None,
            "unresolvedThreads": 0, "merged": False, "state": None, "mergedAt": None}
```

— `scripts/qrspi_pr_state.py:62-65`

```
out[b] = {"merged": False, "prNumber": None, "state": None}   # absent/deleted head ref
```

— `scripts/qrspi_pr_state.py:96`

**Dependencies:** `parse_pr_nodes` (zero-node sentinel) and `stack_merge_state` (deleted-ref sentinel) → `resolve` / `is_stack_fully_merged`.
**Implicit contracts:** No DRAFT awareness anywhere. A MERGED PR is NOT given precedence over a co-existing OPEN/DRAFT PR; precedence is creation order only. Zero-PR and deleted-ref both normalize to `merged: False`, which is safe for cleanup (won't reap) but is exactly what strands a truly-merged branch whose ref was deleted.

## Q12: What do the existing unit tests assume about the number of PRs per branch, and how are PR fixtures constructed (single object vs. list)?

**Answer:** Both test files overwhelmingly assume **one PR per branch**. `qrspi_resolve_state_test.py` builds each phase/slice as a single PR dict (`_phase`, `_slice`) — never a list of competing PRs for one branch. `qrspi_pr_state_test.py` passes single-element node lists to `parse_pr_nodes` and single-element lists to `stack_merge_state` per branch (via the `_node(number, state, merged)` helper that returns a one-element list). The **only** multi-PR test is `"picks first node when multiple returned"` (`:76-81`), which passes two nodes and asserts `nodes[0]` wins — i.e. it pins the current (buggy-for-multi-PR) behavior rather than testing correct disambiguation. There is no fixture for "merged PR + newer closed PR on the same branch."

**Evidence:**

```
def _node(number, state, merged):
    return [{"number": number, "state": state, "merged": merged,
             "reviewDecision": "APPROVED", "reviewThreads": {"nodes": []}}]
```

— `scripts/qrspi_pr_state_test.py:150-152` (and the identical helper in `qrspi_cleanup_test.py:26-30`)

```
check("picks first node when multiple returned",
      parse_pr_nodes([{"number": 100, ...}, {"number": 99, ...}])["number"], 100)
```

— `scripts/qrspi_pr_state_test.py:76-81`

**Dependencies:** `qrspi_resolve_state_test.py`, `qrspi_pr_state_test.py`, `qrspi_cleanup_test.py` all use single-PR-per-branch fixtures via per-test `_node`/`_phase`/`_slice` helpers.
**Implicit contracts:** The test suite's coverage gap IS the latent bug: the `_node` helper hardcodes one PR per branch, so multi-PR selection is untested except for the index-0 pin. A fix must add a multi-PR-per-branch fixture (merged + newer closed) and likely revise/replace the `"picks first node"` assertion.

## Q13: When branch-state determination selects a PR, what is logged or surfaced (PR number chosen, state, why) that would let an operator see which PR was picked and diagnose a wrong-PR selection?

**Answer:** **Almost nothing.** `parse_pr_nodes` emits no log of which node it picked or how many it discarded — it silently takes `nodes[0]`. `qrspi_pr_state.py` only prints the final JSON state (`main`, `:303`) and raises a `RuntimeError` on gh failure (`:224`); it never surfaces the candidate set. `qrspi_resolve.py` likewise only prints the final envelope (`:346`) and has no per-PR logging. The cleanup script's envelope carries `decision`/`reason`/`removed.{branches,remotes}` and `removed` reflects which branches were acted on, but `reason` is a fixed string ("stack fully merged"/"stack not fully merged") that does NOT name which PR's `merged` bool drove the verdict. The batch workflow logs decision/reason at the ticket level (`qrspi-batch.js:679`, `:759`) but not the per-branch PR number selected. An operator cannot see "branch X had PRs #100(closed) and #99(merged); chose #100" from any current output.

**Evidence:**

```
    if res.returncode != 0:
        raise RuntimeError("gh graphql failed for %s: %s" % (head, res.stderr.strip()))
    ...
    json.dump(state, sys.stdout, indent=2); print()
```

— `scripts/qrspi_pr_state.py:223-226, 302-303`

```
    return {"decision": "skip", "reason": "stack not fully merged"}
```

— `scripts/qrspi_cleanup.py:85-88` (reason names no PR)

**Dependencies:** Output is JSON envelope only (`qrspi_pr_state.main`, `qrspi_resolve.build_envelope`, `qrspi_cleanup._envelope`). Batch logs at `.claude/workflows/qrspi-batch.js:679, 759`.
**Implicit contracts:** Observability is "final decision only." The selected PR number is present in the envelope's `phases.*.number` for the resolver path, but the *discarded* candidates and the *selection criterion* are never surfaced. Diagnosing a wrong-PR pick today requires manually re-running the GraphQL query and reading the node list by hand.

---

## Discovered Patterns

- **Single collapse chokepoint.** Every per-branch PR question (advancement AND merge/cleanup) funnels through `parse_pr_nodes` → `nodes[0]`. This is the one place to fix multi-PR selection; both questions inherit whatever it returns. (`scripts/qrspi_pr_state.py:52-76`)
- **Additive-field discipline.** Merge fields (`merged`/`state`/`mergedAt`) were added to `parse_pr_nodes` without disturbing the OPEN-path callers, explicitly documented as ADDITIVE (`:60-61`). A fix can extend the shape similarly without breaking the resolver.
- **Self-locating one-shot scripts.** `qrspi_resolve.py`, `qrspi_cleanup.py` derive `REPO_ROOT` from `__file__` and report any infra error ONCE as `ok:false`, never retrying (motivated by the Ollama path-mangling note). Any new script should follow this.
- **Pure-core / impure-shell split.** Every module separates unit-tested pure functions (`parse_pr_nodes`, `resolve`, `classify_cleanup`, `is_stack_fully_merged`) from subprocess-backed I/O (`_query_pr`, `_run`). Tests target the pure core only.
- **Creation-time is the only ordering key in play.** The codebase never sorts PRs by number or merge state; the sole ordering is GitHub's server-side `CREATED_AT DESC`.
- **All-or-nothing merge semantics.** `is_stack_fully_merged` requires EVERY branch merged; one non-merged (or deleted-ref sentinel) branch blocks reaping for the whole stack.

## Inconsistencies

- **Query fetches 5 PRs, code uses 1.** `PR_QUERY` requests `first:5` PRs per head, but `parse_pr_nodes` uses only `nodes[0]` and discards the other 4. The query's multi-PR capacity is dead — the comment at `:60-61` documents the merge fields as additive but nothing documents that the multi-PR fetch is intentionally collapsed to the newest.
- **`orderBy: CREATED_AT DESC` implies "latest", but "latest-created" ≠ "authoritative/merged".** The sort is named for recency, yet the merge/land question wants the MERGED PR regardless of recency. The query's sort key and the cleanup question's intent diverge — the documented root cause of the wrong-PR stranding (RUS-30/RUS-53).
- **Test pins the buggy behavior.** `"picks first node when multiple returned"` (`qrspi_pr_state_test.py:76-81`) asserts the index-0 collapse as correct, with no co-existing test for "prefer the MERGED PR." The test suite would currently *fail* a correct disambiguation fix at that assertion — it must be revised alongside any fix.
- **Comment claims merge fields are safely additive for "all" callers, but the cleanup path DOES depend on them.** `:60-61` frames `merged`/`state`/`mergedAt` as additive (OPEN-path callers unaffected) — true for the resolver, but the cleanup path's correctness fully depends on `merged` being read from the *right* PR, which the same collapse undermines. The "additive/safe" framing understates that the cleanup question is itself a victim of the index-0 selection.
- **No DRAFT handling despite Q11 raising it.** `isDraft` is neither queried nor referenced anywhere; the schema can't distinguish a DRAFT PR from an OPEN one.
