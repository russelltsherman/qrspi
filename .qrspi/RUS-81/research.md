# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft

## Q1: What GraphQL query does the PR-state gather currently issue, and where in it would a `statusCheckRollup` selection attach without disturbing the existing review-state fields?

**Answer:** The gather issues a single GraphQL query, the module-level constant `PR_QUERY`, via `gh api graphql` (helper `_query_pr`). It selects `repository.pullRequests(headRefName:$head, first:25, orderBy:{field:CREATED_AT, direction:DESC}).nodes` with per-node fields `number, state, merged, mergedAt, reviewDecision, reviewThreads{...}, comments{...}`. There is **NO** check/CI selection today (`grep statusCheckRollup` over the whole repo returns nothing). A `statusCheckRollup` selection (or `commits(last:1){nodes{commit{statusCheckRollup{state}}}}`) would attach as a new sibling field inside the `nodes { ... }` block — additive, alongside `reviewDecision`/`state` — and would be read in `parse_pr_nodes` (Q2) where the other per-node fields are reduced.

**Evidence:**

```
PR_QUERY = """
query($owner:String!, $repo:String!, $head:String!) {
  repository(owner:$owner, name:$repo) {
    pullRequests(headRefName:$head, first:25, orderBy:{field:CREATED_AT, direction:DESC}) {
      nodes {
        number
        state
        merged
        mergedAt
        reviewDecision
        reviewThreads(first:100) { ... }
        comments(first:100) { ... }
      } } } }
"""
```

— `scripts/qrspi_pr_state.py:26-52` (query); `scripts/qrspi_pr_state.py:409-418` (`_query_pr` runs it via `gh api graphql`)
**Dependencies:** `_query_pr` (subprocess `gh`) is the only caller; its node list flows to `parse_pr_nodes`, `select_pr`, `stack_merge_state`. The GraphQL JSON contract is `data.repository.pullRequests.nodes`.
**Implicit contracts:** The query is by `headRefName`, so it still returns nodes for a deleted ref (relied on at `scripts/qrspi_pr_state.py:468-482`). `first:25` + CREATED_AT DESC ordering is assumed by `select_pr`. statusCheckRollup is per-PR-head-commit, so it must come from the latest commit on the PR head.

## Q2: What is the exact shape of the gathered PR object that `qrspi_pr_state.py` emits and `qrspi_resolve_state.py` consumes, and how are additive fields (e.g. `commentTargets`, the merge fields) currently threaded through that shape?

**Answer:** The normalized per-PR shape is produced by `parse_pr_nodes` and is: `{prExists, number, reviewDecision, unresolvedThreads, merged, state, mergedAt, commentTargets}`. `build_state` (the phase assembler) then adds `branchExists` to each phase PR and `n` to each slice PR. Additive fields were threaded by (a) adding the key to BOTH the no-PR default dict and the populated dict in `parse_pr_nodes`, and (b) documenting them as ADDITIVE so existing OPEN-path callers (resolver/restack) that read only `prExists/number/reviewDecision/unresolvedThreads` are unaffected. `commentTargets` is computed by `unaddressed_reviewer_comments(node, bot_login)` and defaults to `[]` when no `bot_login`. The merge fields (`merged/state/mergedAt`) come straight from the node. A new CI enum field would follow the identical pattern: add to both return dicts, document as additive.

**Evidence:**

```
node = select_pr(nodes, prefer="active")
if node is None:
    return {"prExists": False, "number": None,
            "reviewDecision": None, "unresolvedThreads": 0,
            "merged": False, "state": None, "mergedAt": None,
            "commentTargets": []}
...
return {"prExists": True, "number": node.get("number"),
        "reviewDecision": node.get("reviewDecision"),
        "unresolvedThreads": unresolved_thread_count(threads),
        "merged": bool(node.get("merged")), "state": node.get("state"),
        "mergedAt": node.get("mergedAt"), "commentTargets": targets}
```

— `scripts/qrspi_pr_state.py:194-211`
**Dependencies:** Consumed by `qrspi_resolve_state.resolve` via `phases.<name>` and `phases.implementation.slices[]`; resolver predicates `_pr_ready`, `_pr_changes_requested`, `phase_comment_targets`, `design_already_landed` read these keys (`scripts/qrspi_resolve_state.py:90-139`).
**Implicit contracts:** Adding a key requires touching BOTH the empty-default and populated branches of `parse_pr_nodes`, or the no-PR case will be missing the field. The resolver uses `.get(...)` with defaults throughout, so a new field is non-breaking for old states.

## Q3: How does `qrspi_resolve.py` assemble its envelope from the gather plus the resolver decision, and where would a new CI field (and a per-PR attempt count) need to flow through that one-shot orchestrator?

**Answer:** `main()` runs the deterministic sequence: resolve OWNER/REPO via `_gh_name_with_owner`/`parse_name_with_owner`, call `build_state(...)` (the gather), call `resolve(state)` (the decision), provision the worktree, then assemble the JSON envelope via `build_envelope(...)`. `build_envelope` returns `{ok, repoRoot, worktreeDir, existing, decision, commentTargets, reviewers, teamReviewers, ticketContentPath, tip, slices, error?}`. The top-level `commentTargets` is re-emitted from the decision via `comment_targets_of(decision)` because the `decision` dict's key set is fixed and the JS consumer iterates `r.commentTargets`. A new CI field flows automatically inside `state`/`decision` (build_state and resolve are called as opaque pure functions here — no per-field plumbing in `main`), UNLESS the JS consumer must read it at the TOP LEVEL — in which case it needs a re-emit helper like `comment_targets_of` and a new `build_envelope` parameter + key (mirroring `commentTargets`/`tip`/`slices`). A per-PR attempt count is NOT currently in the envelope and has no carrier; it would need either a new gather field (durable source) or a new envelope key.

**Evidence:**

```
state = build_state(owner, repo, args.ticket, args.assigned, args.linear_status, ...)
decision = resolve(state)
worktree = setup_worktree(...)
...
env = build_envelope(worktree, decision, existing, ok=True,
                     reviewers=reviewers, team_reviewers=team_reviewers,
                     ticket_content_path=ticket_content_path,
                     tip=pick_tip(branches, args.ticket),
                     slices=slice_branches(branches, args.ticket),
                     repo_root=repo_root)
```

— `scripts/qrspi_resolve.py:386-401`; `build_envelope` at `scripts/qrspi_resolve.py:190-237`; `comment_targets_of` (top-level re-emit) at `scripts/qrspi_resolve.py:173-187`
**Dependencies:** Imports `build_state` from `qrspi_pr_state`, `resolve` from `qrspi_resolve_state` (`scripts/qrspi_resolve.py:52-53`). Envelope is consumed by `parseResolveEnvelope` in qrspi-batch.js.
**Implicit contracts:** Envelope formatting is byte-pinned by the contract producer test (`json.dumps(env, indent=2)+"\n"` must equal the committed fixture, Q13). A new envelope key requires updating `build_envelope`, the wellformed fixture, and the producer/consumer tests in lockstep.

## Q4: What is the current ordered precedence of decision branches inside the resolver (reset, revise on CHANGES_REQUESTED/comments, advance, wait), and where exactly do the reset check and the frontier feedback handler sit relative to the "wait awaiting review" sink?

**Answer:** `resolve(state)` evaluates branches in this strict order: **(1) Entry gate** (no design phase + not already-landed) → `entry_blocked`/`run_design`; **(2) Reset check** — lowest phase with a NON-frontier `CHANGES_REQUESTED` (something downstream of it) → `reset`; **(2b) Unified feedback handler** — lowest phase carrying a frontier `CHANGES_REQUESTED` OR ≥1 unaddressed comment → `revise`; **(3) Active phase** = highest existing phase: for design/plan → `submit` (no PR) → `wait` (unresolved threads, no CR) → `wait` (not APPROVED) → `advance`; for implementation → completeness gate `advance` → `submit` → `wait` (threads) → `wait` (not all approved) → `land`. The reset check (step 2) and the unified feedback handler (step 2b) BOTH sit AHEAD of the active-phase logic, so they take precedence over every `wait`/`advance`/`land` sink. The "wait awaiting review" sink is the LAST resort within step 3.

**Evidence:**

```
# 1. Entry gate ...   (line 170)
# 2. Reset check ...   (line 190)
cr = [p for p in existing if phase_changes_requested(phases, p)]
if cr:
    k = min(cr, key=_order); above = [p ... _order(p) > _order(k)]
    if above: return decision("reset", ...)
# 2b. Unified feedback handler ...   (line 209)
feedback = [p for p in existing if phase_changes_requested(phases,p) or phase_comment_targets(phases,p)]
if feedback: ... return decision("revise", ...)
# 3. Active phase = highest existing phase.   (line 227)
```

— `scripts/qrspi_resolve_state.py:160-251` (precedence); reset `:190-198`; revise `:209-225`; wait sinks `:241-248`
**Dependencies:** Helpers `phase_changes_requested`, `phase_comment_targets`, `_order`, `_pr_ready`. A CI-driven branch would slot relative to these — most naturally as a new branch in step 2b (auto-revise red frontier) or a new sink near the wait branches.
**Implicit contracts:** `revise` MUST precede `wait`/APPROVED so an approved-but-commented PR is answered, not waited on (documented at `:206-208`). A non-frontier CR never reaches 2b (it resets at 2), so `changeRequested` in a revise decision is True only on the frontier.

## Q5: How does the resolver currently distinguish a *frontier* phase PR from a non-frontier upstream phase PR, and what inputs encode that distinction?

**Answer:** The distinction is purely ordinal, computed from which phases EXIST. `existing = [p for p in PHASES if phase_exists(phases, p)]` where `PHASES = ["design","plan","implementation"]` and `phase_exists` reads `phases.<name>.branchExists`. A phase is the **frontier** when nothing downstream of it exists. The reset check finds the lowest CR phase `k = min(cr, key=_order)` and checks `above = [p for p in existing if _order(p) > _order(k)]`: if `above` is non-empty, `k` is non-frontier → `reset`; if `above` is empty, `k` IS the frontier and falls through to the revise handler. The "active phase" is `max(existing, key=_order)`. The inputs encoding the distinction are `branchExists` per phase (from the gather) and the fixed `PHASES` order.

**Evidence:**

```
existing = [p for p in PHASES if phase_exists(phases, p)]
...
k = min(cr, key=_order)
above = [p for p in existing if _order(p) > _order(k)]
if above:
    return decision("reset", resetToPhase=k, discardPhases=above, ...)
# else: a frontier change request — addressed in place by the unified handler below.
```

— `scripts/qrspi_resolve_state.py:144-145, 190-198`; `phase_exists` `:84-87`; `_order`/`PHASES` `:61, 80-81`
**Dependencies:** `branchExists` is set by `build_state.phase_pr` via `branch_present` (`scripts/qrspi_pr_state.py:466-485`); for implementation, `branchExists = bool(real_snums)` (`scripts/qrspi_pr_state.py:533`).
**Implicit contracts:** "Frontier" is not a stored field — it is derived each call from `existing` + phase order. There is no per-PR frontier flag.

## Q6: What set of action strings does the resolver return today, and which flags/fields accompany the `revise` action that the worker reads?

**Answer:** The legal action vocabulary is the `ACTIONS` tuple: `entry_blocked, run_design, submit, wait, revise, advance, land, reset` (`scripts/qrspi_resolve_state.py:68-77`; mirrored as `RESOLVE_ACTIONS` in JS at `.claude/workflows/qrspi-batch.js:196-198`). Every decision dict has the fixed key set: `{action, phase, nextPhase, resetToPhase, discardPhases, commentTargets, changeRequested, reason}` (built by the local `decision()` helper, `scripts/qrspi_resolve_state.py:147-158`). The `revise` action carries: `phase` (the frontier phase to fix), `commentTargets` (list of unaddressed reviewer comments), and `changeRequested` (bool — whether a formal CR is present). The worker reads `r.commentTargets` (re-emitted at envelope top level) and `r.decision.changeRequested`.

**Evidence:**

```
return decision("revise", phase=f,
                commentTargets=targets,
                changeRequested=cr_present,
                reason="%s PR has %s; address in place%s." % (...))
```

— `scripts/qrspi_resolve_state.py:221-225`; decision key set `:147-158`; ACTIONS `:68-77`
**Dependencies:** `commentTargets` comes from `phase_comment_targets(phases, f)` (`:214`); each target is a CommentTarget dict `{commentId, author, body, threadType, threadId, lastReplyAuthor}` from `unaddressed_reviewer_comments` (`scripts/qrspi_pr_state.py:111-118, 135-142`).
**Implicit contracts:** The decision key set is FIXED — that is exactly why `comment_targets_of` re-emits `commentTargets` to envelope top level (`scripts/qrspi_resolve.py:173-187`). Adding a new revise-accompanying field (e.g. a failing-check name) means extending the `decision()` helper's dict.

## Q7: How does the `revise` worker in the batch orchestrator currently address a frontier feedback PR — which scripts it calls and how it amends and re-pushes the phase commit?

**Answer:** `doRevise(t, r)` runs in two steps within one pass. **Step 1** — per-comment intent engine `respondToComments` spawns one peer-reviewer worker PER `commentTarget`; each ANSWERs / APPLYs+amends / DECLINEs and posts an in-thread reply via `scripts/qrspi_comment_reply.py` (`--body-file` from a token-free staging path). **Step 2a** (comment-only, `!changeRequested`) — return without re-requesting review. **Step 2b** (formal CR) — spawn a finalize worker that: checks out the branch (`gt checkout <id>/<phase>` for design/plan, or per-slice for implementation), reads the CR summary + threads via READ-only `gh pr view`/`gh api graphql`, edits artifacts, then stages+amends in place via `python3 scripts/qrspi_revise_amend.py --ticket <id> --branch <BRANCH>`, then ALWAYS `gt submit --publish --no-edit --rerequest-review ... (--stack for impl)`. Amend is via `qrspi_revise_amend.stage_and_amend` which runs `gt modify --no-interactive -m <existing message verbatim>` (preserving subject+trailers) and VERIFIES the amend captured changes (fails if nothing staged / tree dirty).

**Evidence:**

```
4. ... amend the phase commit IN PLACE by running EXACTLY this one self-locating command:
   `python3 ${engineCmdFor(r, 'scripts/qrspi_revise_amend.py')} --ticket ${t.id} --branch <BRANCH>` ...
5. Re-request review ...: `gt submit --publish --no-edit --rerequest-review${reviewerFlags(r)}${d.phase === 'implementation' ? ' --stack' : ''} --no-interactive`.
```

— `.claude/workflows/qrspi-batch.js:2224-2283` (doRevise); per-comment engine `:2305-...`; amend internals `scripts/qrspi_revise_amend.py:192-227`
**Dependencies:** `doRevise` → `respondToComments` → `qrspi_comment_reply.py`; step 2b → `qrspi_revise_amend.py` + `gt submit`. `engineCmdFor(r, ...)` and `reviewerFlags(r)` build the self-locating paths/flags.
**Implicit contracts:** Re-requesting review flips `reviewDecision` to `REVIEW_REQUIRED` — the ONLY loop-safe termination signal (threads can't be auto-resolved). The amend MUST go through `qrspi_revise_amend.py`; a bare `gt modify --no-interactive` amends an empty index and silently drops edits (HARD STOP rule, `:2272`).

## Q8: What durable cross-run state, if any, does the harness already persist per PR, that an attempt-counter for the loop cap could reuse?

**Answer:** **NO explicit per-PR durable counter or marker exists today.** A grep for `attempt`/`counter`/`marker` in the harness scripts returns nothing. The harness relies entirely on **STRUCTURAL idempotency** derived from observable GitHub state, not on stored markers: (1) the revise loop's termination is the `reviewDecision` flip to `REVIEW_REQUIRED` after re-requesting review (the next gather reads APPROVED/REVIEW_REQUIRED and returns `wait`); (2) comment-reply idempotency is structural — once a bot reply is observed in a thread (or a newer bot top-level comment exists), `unaddressed_reviewer_comments` no longer returns that target, so a second pass does not re-respond (documented at `.claude/workflows/qrspi-batch.js:2301-2304`). The only persisted artifacts are the phase `.md` files (moved by `qrspi_persist.py`) and the commit messages/trailers (preserved verbatim by `qrspi_revise_amend.py`). An attempt-counter would have NO existing carrier to reuse — candidates would be a new marker comment, a commit trailer, or a new gather field, none of which exist now.

**Evidence:**

```
// Idempotency is structural: once a bot reply is observed in the thread (or a newer bot
// top-level comment exists), the gather's unaddressed_reviewer_comments no longer returns
// that target, so a second pass does NOT re-respond — we rely on that, never on local state.
```

— `.claude/workflows/qrspi-batch.js:2301-2304`; revise termination contract `scripts/qrspi_resolve_state.py:40-49`
**Dependencies:** Cross-run state is read entirely from `gh` GraphQL (review decision, thread/comment state) each run — there is no local state file. `qrspi_revise_amend.py` deliberately does NOT compare/track OIDs (`scripts/qrspi_revise_amend.py:124-...`).
**Implicit contracts:** The harness is designed to be STATELESS across runs (the resolver "reconciles on the next run", `.claude/workflows/qrspi-batch.js:222`). Any attempt-counter must either become observable-from-GitHub or break the stateless-reconciliation invariant.

## Q9: How is the implementation phase represented across multiple slice PRs in the resolver state, such that a CI failure on *any* slice PR can be attributed to the single implementation phase?

**Answer:** Implementation is ONE logical phase backed by a list of slice PRs. In the gather, `phases.implementation = {branchExists, slices[], expectedSlices, prSummaryCommitted}` where `slices` is a list of per-PR shapes each carrying `n` (slice number). The resolver treats the stack as a whole via "any slice" aggregation: `phase_changes_requested("implementation")` returns True if ANY slice PR has CR (`any(_pr_changes_requested(s) for s in _impl_slices(phases))`); `phase_comment_targets("implementation")` concatenates `commentTargets` across all slices; the land/wait gates use `any(...)`/`all(...)` over `slices`. So a CI failure on any one slice PR would be attributed to the implementation phase by the same "any slice" pattern.

**Evidence:**

```
def phase_changes_requested(phases, name):
    if name == "implementation":
        return any(_pr_changes_requested(s) for s in _impl_slices(phases))
    return _pr_changes_requested(phases.get(name, {}))
```

— `scripts/qrspi_resolve_state.py:102-107`; comment aggregation `:130-139`; impl gates `:265-292`; `_impl_slices` `:98-99`
**Dependencies:** `_impl_slices(phases)` reads `phases.implementation.slices`; populated by `build_state` slice loop (`scripts/qrspi_pr_state.py:488-493`, sets `pr["n"]=n`).
**Implicit contracts:** The stack is "reviewed as a whole" — a CR/comment on any slice is the phase's CR/comment. A CI-on-impl branch should follow the same `any(...)` pattern to stay consistent (the existing `wait`/`land` gates already use `any`/`all` over slices, `:278-290`).

## Q10: How does the gather currently represent a PR with **no checks** versus a null/absent rollup, and how would the normalizer map SUCCESS / FAILURE / ERROR / PENDING / EXPECTED / null to a small enum?

**Answer:** **The gather does NOT currently fetch or represent checks at all** — there is no `statusCheckRollup` selection in `PR_QUERY` and no check field in the normalized shape (Q1, Q2). So today there is no distinction between "no checks" and "null rollup"; both are simply absent. The closest existing normalization PATTERN to follow is `reviewDecision` (GitHub returns it as `null` until a review exists; `parse_pr_nodes` passes the raw value and the resolver treats `null` as "awaiting review", `scripts/qrspi_pr_state.py:176-179`) and `unresolved_thread_count` (a pure reducer with a `(x or [])` guard, `scripts/qrspi_pr_state.py:57-60`). A new normalizer would mirror these: a pure function mapping GitHub's `statusCheckRollup.state` (`SUCCESS/FAILURE/ERROR/PENDING/EXPECTED`) plus `null`/absent-rollup to a small enum (e.g. green/red/pending/none), guarded with `.get(...) or` defaults, and unit-tested like `unresolved_thread_count`.

**Evidence:**

```
def unresolved_thread_count(review_threads):
    """Count threads whose isResolved is falsey. ..."""
    return sum(1 for t in (review_threads or []) if not t.get("isResolved"))
```

— `scripts/qrspi_pr_state.py:57-60` (the reducer pattern); reviewDecision null-handling note `:176-179`
**Dependencies:** A check enum field, once added to `parse_pr_nodes`, would be read by the resolver via `phases.<name>.<field>`.
**Implicit contracts:** Pure parsers tolerate `None`/missing with `(x or [])` / `.get(...)` guards and are unit-tested in isolation; subprocess calls are not tested. GitHub's `statusCheckRollup` is null when no checks have run — the normalizer must distinguish that from FAILURE.

## Q11: What does the resolver do today when a frontier PR simultaneously carries a CHANGES_REQUESTED (or unaddressed comments) and is otherwise advanceable?

**Answer:** The unified feedback handler (step 2b) runs AHEAD of the advance/wait/land logic, so a frontier PR with CR and/or comments ALWAYS resolves to `revise` regardless of whether it is otherwise advanceable. The feedback set is `[p for p in existing if phase_changes_requested(p) or phase_comment_targets(p)]`; the lowest such phase is chosen (`f = min(feedback, key=_order)`). When both signals are present on `f`, `cr_present=True` and `targets` non-empty, the reason says "a change request and unaddressed reviewer comment(s)" and the worker handles both in one pass. Crucially, this fires EVEN WHEN the PR is APPROVED (documented: "an approved-but-commented PR is answered, not waited on", `:206-208`). Competing signals are ordered by: reset (non-frontier CR) > revise (frontier CR and/or comments) > advance/wait/land.

**Evidence:**

```
feedback = [p for p in existing
            if phase_changes_requested(phases, p) or phase_comment_targets(phases, p)]
if feedback:
    f = min(feedback, key=_order)
    cr_present = phase_changes_requested(phases, f)
    targets = phase_comment_targets(phases, f)
    if cr_present and targets:  what = "a change request and unaddressed reviewer comment(s)"
    ...
    return decision("revise", phase=f, commentTargets=targets, changeRequested=cr_present, ...)
```

— `scripts/qrspi_resolve_state.py:209-225`
**Dependencies:** `phase_changes_requested`, `phase_comment_targets` (both "any slice" for implementation).
**Implicit contracts:** Ordering precedence is the conflict resolution mechanism — there is no scoring; the FIRST matching branch in source order wins. A new CI signal must declare its precedence relative to reset/revise/wait.

## Q12: How does the resolver behave today for a PENDING/in-flight CI state given it ignores CI entirely, and what is the current path that such a PR takes to `wait`?

**Answer:** The resolver IGNORES CI completely (no CI field is gathered or read). A PR with in-flight/pending CI is decided solely on review state: in the active-phase block, if its PR exists, has no unresolved threads, and is NOT APPROVED, it falls to `wait` with reason `"<phase> PR awaiting review (reviewDecision=<...>)"`. If it IS approved+clean it would `advance`/`land` (CI is never consulted, so a green-but-pending distinction does not exist today). For implementation, the equivalent path is `"Not all slice PRs are approved yet."` → `wait`. So a pending-CI PR today takes the ordinary "awaiting review" path to `wait` (or advances if reviewer-approved), with no awareness that checks are still running.

**Evidence:**

```
if pr.get("reviewDecision") != "APPROVED":
    return decision("wait", phase=active,
                    reason="%s PR awaiting review (reviewDecision=%s)." % (active, pr.get("reviewDecision")))
```

— `scripts/qrspi_resolve_state.py:245-248`; implementation equivalent `:288-290`
**Dependencies:** Only `reviewDecision` and `unresolvedThreads` gate this path.
**Implicit contracts:** Approval is the sole advancement authority today ("PR review state — not Linear status — is the authority"). Introducing CI means a PENDING state needs an explicit decision (most consistently: route to `wait` so the harness does not auto-revise a still-running build).

## Q13: What is the existing unit-test convention for the resolver and gather (fixtures, table-driven cases, the JS↔Python contract-fixture seam), and where are the seam fixtures defined?

**Answer:** Tests are **stdlib-only, assert-based** (no pytest), run with `python3 scripts/<name>_test.py`, exit 0/1. **Resolver** (`qrspi_resolve_state_test.py`): TABLE-DRIVEN — builders `_phase/_impl/_slice/_ct/state`, a `case(name, st, expect)` accumulator into `CASES`, then a runner asserts `resolve(st)` matches `expect` (with a `contains` substring helper for reasons). **Gather** (`qrspi_pr_state_test.py`): direct `check(name, got, want)` assertions over the pure parsers (`parse_pr_nodes`, `select_pr`, `unresolved_thread_count`, `stack_merge_state`) with inline GraphQL-node literals; `_node`/`_nodes` builders for stack cases. **Contract seam**: fixtures live at `scripts/fixtures/contract_seam/<seam>/*.json` (seams: cleanup, config, critics, land, ordered-tickets, **resolve**, restack, sync-trunk). The PRODUCER test (`qrspi_contract_fixtures_producer_test.py`) asserts each builder's `json.dumps(..., indent=2)+"\n"` byte-matches the committed `wellformed.json`; the CONSUMER test (`qrspi_contract_fixtures_consumer_test.py`) drives `scripts/contract_seam_runner.js` (the JS parsers) against the fixtures. The aggregating runner is `python3 scripts/run_tests.py`.

**Evidence:**

```
def case(name, st, expect):
    CASES.append((name, st, expect))
case("entry: assigned + Selected -> run_design",
     state(assigned=True, linear="Selected", phases={}),
     {"action": "run_design", "phase": "design"})
```

— `scripts/qrspi_resolve_state_test.py:60-75`; gather `check()` `scripts/qrspi_pr_state_test.py:28-83`; producer byte-pin `scripts/qrspi_contract_fixtures_producer_test.py:81-106`; resolve fixtures `scripts/fixtures/contract_seam/resolve/{wellformed,prose_wrapped,no_json,unknown_action}.json`
**Dependencies:** Producer test imports `qrspi_resolve_state` + `qrspi_resolve` and builds the envelope through `build_envelope` (`scripts/qrspi_contract_fixtures_producer_test.py:54, 81-106`). Consumer test runs `contract_seam_runner.js parseResolveEnvelope` (`scripts/qrspi_contract_fixtures_consumer_test.py:108-118`).
**Implicit contracts:** New resolver cases are added by appending `case(...)`. A new envelope field forces a synchronized update of `wellformed.json` + producer test (byte-for-byte) + consumer parser validation.

## Q14: Is there a JS DEFAULT mirror of the resolver logic that must stay in lockstep, and where does the contract-fixture test assert parity between it and the Python resolver?

**Answer:** **NO — there is no JS mirror of the RESOLVER decision logic.** The batch orchestrator does NOT re-derive any resolver logic; it calls `qrspi_resolve.py` (which calls the Python `resolve`) and merely DISPATCHES on `decision.action` in a `switch` (`.claude/workflows/qrspi-batch.js:2788-2802`). The only JS-side resolver-adjacent code is `parseResolveEnvelope`/`RESOLVE_ACTIONS`, which VALIDATE the envelope shape (that `decision.action` is one of the 8 legal actions) — not re-implement the decision. The "DEFAULT mirror" that the codebase keeps in lockstep is the **critic config** (`DEFAULT_CRITIC_PHASES`/`DEFAULT_DESIGN_LENSES` in qrspi-batch.js), whose parity with `qrspi_critics_config.py` IS asserted in `scripts/qrspi_critics_config_test.py:272` ("default diverged between Python and JS mirror"). The resolver itself has a single source of truth in Python; the contract-seam test asserts the JS PARSER accepts the Python PRODUCER's envelope, not decision parity. So Q14's premise (a JS DEFAULT resolver mirror) does not hold for the resolver.

**Evidence:**

```
const a = r.decision.action
...
case 'run_design': res = await doDesign(t, r); break
case 'advance': ...
case 'revise': res = await doRevise(t, r); break
case 'land': res = await doLand(t, r); break
```

— `.claude/workflows/qrspi-batch.js:2788-2802` (dispatch only); `RESOLVE_ACTIONS`/`parseResolveEnvelope` `:196-238`; critic-config (not resolver) JS↔Python parity `scripts/qrspi_critics_config_test.py:272`
**Dependencies:** JS depends on Python's resolver via the resolve envelope; no logic duplication. The contract-seam resolve fixtures test envelope shape parsing, not decision equivalence.
**Implicit contracts:** Resolver decision logic lives ONLY in `scripts/qrspi_resolve_state.py`; the design doc states "the orchestrator and batch both call it rather than re-deriving state logic" (`.claude/CLAUDE.md`). A new resolver action requires updating BOTH `ACTIONS` (Python) and `RESOLVE_ACTIONS` (JS validation set) — that is the one place a JS↔Python value must stay in lockstep for the resolver, plus a `switch` case + `doX` handler in JS.

## Q15: How does the `revise` worker currently read failing run/check output to diagnose a problem, and what diagnostic detail from `statusCheckRollup` is available to the worker to know *which* check failed?

**Answer:** **The revise worker does NOT read CI run/check output at all.** Its diagnostic inputs are REVIEW feedback only: the CHANGES_REQUESTED review SUMMARY body and unresolved thread comments, read via READ-only `gh pr view` / `gh api graphql` queries (`.claude/workflows/qrspi-batch.js:2264, 2268`), plus the `commentTargets` already gathered (each carrying `commentId, author, body, threadType, threadId, lastReplyAuthor`). There is no `gh run view`/`gh run list`/checks invocation anywhere in the revise path (or the whole orchestrator). Because the gather fetches no `statusCheckRollup`, **zero check diagnostic detail is currently available to the worker** — it cannot know which check failed. To diagnose a failing check, the gather would need to add `statusCheckRollup` (with per-`contexts` node `name`/`conclusion`/`detailsUrl`), the resolver/envelope would need to carry it (Q3), and the revise prompt would need a step to read failing-check logs (e.g. `gh run view <run-id> --log-failed`).

**Evidence:**

```
2. Read the change request: the CHANGES_REQUESTED review SUMMARY body AND any unresolved
   thread comments not already addressed (READ-only queries per the SKILL).
- ... Reading feedback via `gh pr view`/`gh api graphql` queries is fine. ...
```

— `.claude/workflows/qrspi-batch.js:2264-2268`; CommentTarget shape `scripts/qrspi_pr_state.py:111-118`; no check fetch in `PR_QUERY` `scripts/qrspi_pr_state.py:26-52`
**Dependencies:** Worker diagnostics depend solely on review-state fields from the gather + ad-hoc `gh pr view`/`gh api graphql` reads it performs itself.
**Implicit contracts:** The worker is HONESTY-BOUND ("never fabricate a fix"), so any CI-driven diagnosis must come from real fetched check data, not invention. `statusCheckRollup.contexts.nodes` (CheckRun: `name`, `conclusion`, `detailsUrl`; StatusContext: `context`, `state`, `targetUrl`) is the GitHub source that would name the failing check.

---

## Discovered Patterns

- **Pure functional core / imperative shell, strictly separated.** Every Python script splits "pure parsers (unit-tested)" from "subprocess-backed mechanics (not unit-tested)" with explicit banner comments (e.g. `scripts/qrspi_pr_state.py:55, 362`). New CI logic is expected to be a pure normalizer + a thin subprocess fetch.
- **Additive-field discipline.** New fields on the gathered PR shape, the decision dict, and the envelope are always documented as ADDITIVE and added to BOTH the empty-default and populated branches, with `.get(...)`/`(x or [])` guards on the read side so old states never break (`scripts/qrspi_pr_state.py:184-211`; resolver predicates `scripts/qrspi_resolve_state.py:90-139`).
- **Statelessness / structural idempotency.** The harness stores no per-PR run state; every decision is re-derived each run from GitHub-observable state, and loop termination relies on an OBSERVABLE flip (reviewDecision → REVIEW_REQUIRED, or a bot reply appearing in a thread). This is a deliberate invariant an attempt-counter (Q8) would have to respect or explicitly break.
- **Precedence-ordered decision branches, no scoring.** The resolver resolves competing signals purely by source-order precedence (reset > revise > active-phase submit/wait/advance/land). A new CI branch must declare its slot.
- **"Any slice" aggregation for the implementation phase.** Multi-PR implementation is collapsed to one phase via `any(...)`/`all(...)` over `slices` (CR, comments, threads, approval) — the template a CI-on-impl signal should follow.
- **Byte-pinned contract fixtures.** The JS↔Python seam is guarded by producer tests that byte-match `json.dumps(env, indent=2)+"\n"` against committed `wellformed.json`, plus consumer tests running the real JS parsers — so any envelope-shape change is a 3-file synchronized edit.
- **Self-locating scripts + token-free staging.** Path-sensitive scripts derive paths from `__file__`/git-common-dir; the orchestrator passes file PATHS (never fragile bodies) through `engineCmdFor(r, ...)` and `/tmp/phase-stage/...` to keep the weak worker model from corrupting tokens.

## Inconsistencies

- **Q14 premise vs. reality:** The questions assume "a JS DEFAULT resolver mirror that must stay in lockstep." No such mirror exists — the resolver decision logic is Python-only, and the JS side only validates `decision.action` against `RESOLVE_ACTIONS` and dispatches. The actual JS↔Python "DEFAULT mirror" the codebase maintains is the **critic config** (`DEFAULT_CRITIC_PHASES`), asserted in `qrspi_critics_config_test.py:272`. The only resolver value that must stay in lockstep is the action vocabulary (`ACTIONS` in Python ↔ `RESOLVE_ACTIONS` in JS).
- **CI is entirely absent today.** Questions Q1/Q10/Q12/Q15 ask how the harness represents/reacts to CI check state; the codebase has NO `statusCheckRollup` fetch, no check enum, and no check-reading in the revise worker (grep for `statusCheckRollup|checkSuite|CheckRun` over scripts/.claude/docs returns nothing). All CI-related answers describe the PATTERN a new field would follow, not existing behavior.
- **`changeRequested` is True only on the frontier, by construction.** The module docstring and the reset/revise split guarantee a non-frontier CR resets before reaching the revise handler — so the worker can assume `changeRequested` implies frontier. This is an implicit, undocumented-in-the-decision-dict contract (the field carries no frontier flag of its own; frontier-ness is re-derived each call from `existing`).
- **`exists_locally` is a documented no-op input** to `branch_present` (`scripts/qrspi_pr_state.py:308-339`) — accepted "for contract symmetry" but never used in the gate. A reader of the signature could wrongly assume local existence is a presence signal.
