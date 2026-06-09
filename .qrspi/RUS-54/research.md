# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-08T00:00:00Z
**Generated:** 2026-06-08T00:00:00Z
**Status:** draft

## Q1: How does `scripts/qrspi_pr_state.py` currently gather PR review state via the gh GraphQL query, and which fields (review decision, review threads, comments, authors) are already fetched versus absent?

**Answer:** A single GraphQL query `PR_QUERY` fetches, per head ref, the newest 25 PRs and for each: `number`, `state`, `merged`, `mergedAt`, `reviewDecision`, and `reviewThreads(first:100){ nodes { isResolved } }`. **Only the boolean `isResolved` is fetched per thread** — there are NO comment fields (no `comments`, no `id`, no `body`, no `author`/`user`, no `path`, no `databaseId`, no `in_reply_to`). The gather reduces threads to a single integer `unresolvedThreads` via `unresolved_thread_count()` (counts threads where `isResolved` is falsey). So per-comment data (id, author, body, thread association, reply target) is entirely ABSENT from this query and from the normalized state. The subprocess `_query_pr()` shells out `gh api graphql` and returns `data.repository.pullRequests.nodes`; `parse_pr_nodes()` then normalizes one node to `{prExists, number, reviewDecision, unresolvedThreads, merged, state, mergedAt}`.

**Evidence:**

```
pullRequests(headRefName:$head, first:25, orderBy:{field:CREATED_AT, direction:DESC}) {
  nodes {
    number
    state
    merged
    mergedAt
    reviewDecision
    reviewThreads(first:100) { nodes { isResolved } }
  }
}
```

— `scripts/qrspi_pr_state.py:26-41`

```
threads = (node.get("reviewThreads") or {}).get("nodes", [])
return {
    "prExists": True,
    "number": node.get("number"),
    "reviewDecision": node.get("reviewDecision"),
    "unresolvedThreads": unresolved_thread_count(threads),
    ...
```

— `scripts/qrspi_pr_state.py:100-109`

**Dependencies:** Upstream: `gh` CLI (graphql), `git`. Downstream consumer: `qrspi_resolve_state.resolve()` reads only `reviewDecision`/`unresolvedThreads`/`prExists`/`number`/slice list. `qrspi_resolve.build_state()` calls this module's `build_state`.
**Implicit contracts:** `reviewDecision` null is normalized to `None` (treated as "awaiting review"). Thread state is reduced to a count; no comment identity survives the gather. A `gh graphql` non-zero exit raises `RuntimeError` (the gather aborts rather than degrading).

## Q2: What is the shape of the state envelope that `scripts/qrspi_resolve.py` returns to the orchestrator, and where in that envelope would per-comment data (id, author, body, thread association, in_reply_to_id) need to flow to reach the action decision?

**Answer:** `qrspi_resolve.py` returns a JSON envelope assembled by `build_envelope()`: `{ ok, repoRoot, worktreeDir, existing{...artifact booleans}, decision{...}, reviewers, teamReviewers, ticketContent, error? }`. The `decision` sub-object is exactly `qrspi_resolve_state.resolve()`'s output: `{action, phase, nextPhase, resetToPhase, discardPhases[], reason}`. The PR review state (`state` from `build_state`, including `phases.<name>` with `reviewDecision`/`unresolvedThreads`/`number`) is consumed internally to compute `decision` but is **NOT** re-emitted in the envelope — only the resolved `decision` survives. Per-comment data would have to enter at TWO points: (1) `build_state()` in `qrspi_pr_state.py` would need to fetch and carry per-thread/per-comment fields into `phases.<name>`; (2) the envelope would need a new field (e.g. `phases` or `comments`) on the `build_envelope` output because today `resolve()` returns only the decision, so a comment-response action would have nowhere to carry comment ids/thread targets to the orchestrator/agent.

**Evidence:**

```
env = {
    "ok": ok,
    "repoRoot": REPO_ROOT,
    "worktreeDir": worktree_dir,
    "existing": existing,
    "decision": decision,
    "reviewers": reviewers,
    "teamReviewers": team_reviewers,
    "ticketContent": ticket_content,
}
```

— `scripts/qrspi_resolve.py:191-200`

```
state = build_state(owner, repo, args.ticket, args.assigned, args.linear_status, trunk=args.trunk)
decision = resolve(state)
worktree = setup_worktree(...)
existing = detect_existing(os.path.join(worktree, ".qrspi", args.ticket))
reviewers, team_reviewers = load_reviewers()
env = build_envelope(worktree, decision, existing, ok=True, ...)
```

— `scripts/qrspi_resolve.py:327-337`

**Dependencies:** `qrspi_resolve.py` imports `build_state` from `qrspi_pr_state` and `resolve` from `qrspi_resolve_state`. The JS orchestrator `parseResolveEnvelope()` validates `ok`, `worktreeDir`, `decision.action`.
**Implicit contracts:** The envelope is the SOLE channel from script to orchestrator; the raw `state` is discarded. `decision` keys are fixed (any new action must still be one of `RESOLVE_ACTIONS` in the JS). `worktreeDir` must end with `/.worktrees/<ticketId>` or the JS rejects the envelope.

## Q3: How does the batch workflow consume the resolved action and pass per-ticket context into the spawned phase agent prompt, so a new "respond to comment" action could carry comment ids and thread targets?

**Answer:** The main loop calls `resolveTicket(t)` → `parseResolveEnvelope` → `r` (the envelope), then `switch (r.decision.action)` dispatches to a `do<Action>(t, r)` handler. Each handler reads context off `r`: `r.worktreeDir`, `r.decision.phase`/`nextPhase`/`resetToPhase`/`discardPhases`, `r.ticketContent`, `r.existing`, `r.reviewers`/`teamReviewers` (via `reviewerFlags(r)`), `r.repoRoot`. Handlers build the phase-agent prompt as a template literal interpolating those fields, then call `agent(prompt, {label, phase, agentType, schema?})`. A new "respond to comment" action would add a `case` in the `switch` (and to `RESOLVE_ACTIONS`), a `do<Respond>(t, r)` handler, and would read comment ids/thread targets off `r.decision` (or a new envelope field) to interpolate into its worker prompt — exactly how `doRevise` reads `r.decision.phase` and `r.repoRoot` to build the revise prompt.

**Evidence:**

```
switch (a) {
  case 'run_design': res = await doDesign(t, r); break
  case 'advance': ...
  case 'submit': res = await doSubmit(t, r); break
  case 'reset': res = await doReset(t, r); break
  case 'revise': res = await doRevise(t, r); break
  case 'land': res = await doLand(t, r); break
  case 'wait':
  case 'entry_blocked':
  default:
    res = skip(t, r.decision, `Skipped (${a}): ${r.decision.reason}`)
```

— `.claude/workflows/qrspi-batch.js:849-864`

**Dependencies:** `agent()` (workflow runner spawns typed `.claude/agents/qrspi-*`). `RESOLVE_ACTIONS` set (line 104-105) gates which actions the parser accepts.
**Implicit contracts:** Each action drives at most ONE autonomous step per ticket per run. The `switch` default routes unknown/`wait`/`entry_blocked` actions to `skip()`. Any new action MUST be added to `RESOLVE_ACTIONS` or `parseResolveEnvelope` rejects the envelope as "unknown decision.action".

## Q4: What inputs and outputs does the tested resolver `scripts/qrspi_resolve_state.py` expose, and how does it currently classify a PR with unresolved threads but no CHANGES_REQUESTED as `wait`?

**Answer:** `resolve(state)` is a pure function: input is the normalized state dict (`{ticketId, assigned, linearStatus, phases{design, plan, implementation}}`); output is `{action, phase, nextPhase, resetToPhase, discardPhases[], reason}`. `main()` reads state JSON from `--state` file or stdin and dumps the decision. For an active design/plan PR, after the reset check has already handled CHANGES_REQUESTED, if `pr.unresolvedThreads > 0` it returns `wait` with the reason that threads cannot be auto-resolved and are left for the reviewer. The same logic applies in the implementation branch (`any(s.unresolvedThreads > 0 ...)` → `wait`). The rationale (cited in the docstring) is that GitHub thread mutations 403 on this cross-owned repo, so an autonomous revise could never clear the thread gate and would loop.

**Evidence:**

```
if pr.get("unresolvedThreads", 0) > 0:
    # ... this is a PR with lingering review threads but NO formal change request.
    return decision("wait", phase=active,
                    reason="%s PR has %d unresolved review thread(s) and no change "
                           "request; left for the reviewer to resolve ..." % (active, pr["unresolvedThreads"]))
```

— `scripts/qrspi_resolve_state.py:134-143`

**Dependencies:** Pure; no I/O. Called by `qrspi_resolve.resolve()` and (per docstring) the qrspi-work SKILL / batch.
**Implicit contracts:** `READY(pr)` = `reviewDecision == "APPROVED" AND unresolvedThreads == 0`. The decision is a single action; the resolver performs no comment inspection because comment data is not in `state`. A thread-only PR is terminal-for-automation (`wait`), explicitly to avoid an unbreakable revise loop.

## Q5: Which gh REST/GraphQL calls and comment-write paths are already invoked anywhere in the codebase, and where would a reply-write helper be wired in?

**Answer:** The ONLY gh GraphQL call invoked from a script is the **read-only** `PR_QUERY` in `qrspi_pr_state._query_pr()` (`gh api graphql ... pullRequests`). The SKILL documents additional **read-only** queries the revise worker may run (`gh pr view --json reviews,comments`, and a `reviewThreads{...comments{nodes{path body}}}` GraphQL read). **There is NO comment-write path anywhere** — no `gh api -X POST`, no `/pulls/{n}/comments/{id}/replies`, no `gh pr comment`, no `gh api --method POST` for PR comments. The codebase explicitly forbids gh PR writes: every revise/wait path says "every authenticated gh PR write 403s on this cross-owned repo." `mcp__linear__save_comment` exists in the SKILL allowed-tools but writes **Linear issue comments**, not GitHub PR review-thread replies. A reply-write helper would be net-new; by convention (`qrspi_pr_body.py`, `qrspi_revise_amend.py`) it would be a self-locating `scripts/qrspi_*.py` script invoked verbatim by a worker, returning a JSON envelope.

**Evidence:**

```
res = subprocess.run(
    ["gh", "api", "graphql",
     "-f", "query=%s" % PR_QUERY,
     "-F", "owner=%s" % owner, "-F", "repo=%s" % repo, "-F", "head=%s" % head],
    capture_output=True, text=True)
```

— `scripts/qrspi_pr_state.py:264-269` (the only gh graphql call; read-only)

```
- DO NOT attempt to resolve or reply to review threads, and DO NOT run any `gh pr`/GraphQL mutation: every authenticated gh PR write 403s on this repo. Reading feedback via `gh pr view`/`gh api graphql` queries is fine.
```

— `.claude/workflows/qrspi-batch.js:614`

**Dependencies:** `gh` CLI. Reviewer requests go through `gt submit --reviewers` (Graphite's App credential), not gh — that is the one write path that works.
**Implicit contracts:** Writes to the PR (body, comments, threads) are ONLY possible via Graphite's GitHub-App credential at `gt submit` creation time; the gh PAT 403s on all authenticated PR writes. NOTE: the global MEMORY records this 403 as RESOLVED 2026-06-08 (bot switched to a classic PAT; gh PR comment writes now succeed) — but NO code reflects that yet; every in-repo comment/doc still asserts the 403 (see Inconsistencies).

## Q6: How are reviewer identities and the bot identity (`russelltshermanbot`) currently determined — is there existing author/`@me` resolution that distinguishes reviewer-authored from bot-authored comments?

**Answer:** Reviewer identities are resolved in `qrspi_resolve.py`: `load_reviewers()` reads optional `.qrspi/config.json` (`reviewers`/`teamReviewers`), defaulting to `["@me"]`. The `@me` sentinel is expanded to the gh-authenticated login via `_gh_authenticated_login()` (`gh api user -q .login`), only when `references_me(config)` is true. `resolve_reviewers(config, me_login)` is the pure expansion. There is NO bot-identity constant (`russelltshermanbot` appears only in global MEMORY, not in repo code) and **NO author-attribution logic** anywhere — nothing distinguishes a reviewer-authored comment from a bot-authored reply, because comment authors are never fetched (Q1). The only identity resolution that exists is "who to REQUEST review FROM" (the reviewer login), not "who AUTHORED a comment."

**Evidence:**

```
def resolve_reviewers(config, me_login):
    raw_revs = select_source(config, "reviewers", ["@me"])
    revs = []
    for tok in raw_revs:
        if tok.lower() == "@me":
            if me_login:
                revs.append(me_login)
        else:
            revs.append(tok)
    teams = select_source(config, "teamReviewers", [])
    return _dedupe_ci(revs), _dedupe_ci(teams)
```

— `scripts/qrspi_resolve.py:100-118`

```
def _gh_authenticated_login():
    rc, out, _ = _run(["gh", "api", "user", "-q", ".login"], cwd=REPO_ROOT)
    login = out.strip()
    return login if (rc == 0 and login) else None
```

— `scripts/qrspi_resolve.py:222-228`

**Dependencies:** `gh api user`, `.qrspi/config.json` (gitignored; example at `.qrspi/config.example.json`).
**Implicit contracts:** Reviewer config is best-effort; failures degrade to `("","")` (omit the flag). `@me` is the portable default so no username is hard-coded. NO bot-vs-reviewer author discrimination exists to reuse — a comment-response feature would need new author resolution (e.g. compare comment `author.login` against the authenticated/bot login).

## Q7: How is comment/thread idempotency state represented today — is there any persisted record of which comment ids the agent has already replied to, and where would such a marker live relative to `.qrspi/<id>/` artifacts?

**Answer:** **There is NO comment/thread idempotency state of any kind.** A grep for `idempot|replied|in_reply_to|repliedTo` finds only command-level idempotency (restack/cleanup/clear-stale-pr are idempotent operations) — none track comment reply history. `.qrspi/<id>/` holds only phase ARTIFACTS: `questions.md, research.md, design.md, structure.md, plan.md, worktree.md, impl-log.md, pr-summary.md` (the `ARTIFACTS` list in `qrspi_resolve.py:47` / `qrspi_persist.py:43`). No per-comment marker file exists. `qrspi_persist.py` moves staged artifacts to `.worktrees/<id>/.qrspi/<id>/<name>.md` and verifies non-empty; it knows nothing of comments. A "which comment ids have been replied to" marker would be net-new — logically it would live alongside artifacts under `.qrspi/<id>/` (e.g. a `comment-replies.json` state file), but no such convention exists today. The current loop-safe termination signal is the `reviewDecision` flip (REVIEW_REQUIRED after rerequest), not any persisted comment ledger.

**Evidence:**

```
ARTIFACTS = ["questions", "research", "design", "structure", "plan", "worktree"]
```

— `scripts/qrspi_persist.py:43` (and identically `qrspi_resolve.py:47`)

```
def dest_path(repo_root, ticket, artifact):
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket, "%s.md" % artifact)
```

— `scripts/qrspi_persist.py:58-62`

**Dependencies:** `qrspi_persist.py` (artifact mover). The `.qrspi/<id>/` directory.
**Implicit contracts:** Idempotency in this codebase is achieved by re-derivable STATE (resolver recomputes the action from PR/git state on each run), NOT by persisted ledgers. Termination of an autonomous loop relies on a state flip the next gather observes (e.g. CHANGES_REQUESTED → REVIEW_REQUIRED). A comment-reply has no equivalent observable flip (a reply does not change `reviewDecision` or `isResolved`).

## Q8: How does the resolver currently order competing actions (advance, submit, land, reset, revise, wait) for a single ticket, and where would a comment-response action be prioritized among them?

**Answer:** `resolve()` is a strict priority cascade with early returns: (1) **Entry gate** — no design branch → `entry_blocked`/`run_design`. (2) **Reset check** — the LOWEST existing phase carrying CHANGES_REQUESTED wins; if phases exist above it → `reset` (discard downstream); else (it is the frontier) → `revise`. (3) **Active phase** = highest existing phase; then in order: no PR → `submit`; unresolved threads (no CR) → `wait`; not APPROVED → `wait`; APPROVED+clean and not top → `advance`; implementation complete+approved → `land`. So CHANGES_REQUESTED (reset/revise) OUTRANKS everything below the entry gate; threads→wait sits below the reset check. A comment-response action would slot AFTER the reset/revise check (so a formal CR still takes precedence) but could be prioritized ABOVE the `wait` returns — i.e. where today a thread-only PR returns `wait`, a comment-response could fire instead, since `wait` is the current terminal for "threads exist but no CR."

**Evidence:**

```
# 1. Entry gate ...
if "design" not in existing: ...
# 2. Reset check — lowest existing phase carrying CHANGES_REQUESTED wins.
cr = [p for p in existing if phase_changes_requested(phases, p)]
if cr:
    k = min(cr, key=_order)
    above = [p for p in existing if _order(p) > _order(k)]
    if above: return decision("reset", ...)
    return decision("revise", ...)
# 3. Active phase = highest existing phase.
active = max(existing, key=_order)
```

— `scripts/qrspi_resolve_state.py:101-127`

**Dependencies:** Pure; `PHASES = ["design","plan","implementation"]` and `_order()` define precedence.
**Implicit contracts:** CHANGES_REQUESTED always outranks thread/approval handling (a guard test pins "CR outranks threads"). The `wait` return is the explicit "nothing autonomous to do" sink for a thread-only PR — the natural insertion point for a comment-response action.

## Q9: How does the current thread-gathering logic distinguish a reviewer-authored comment from a bot-authored reply, and does the existing JSON parsing risk capturing the nested `user.id` instead of the comment `.id` field?

**Answer:** It does NEITHER and risks NEITHER, because **no comment-level data is fetched or parsed at all**. `unresolved_thread_count()` consumes only `[{isResolved: bool}, ...]` — there are no `id`, `user`, `author`, or `body` fields in the query (Q1), so there is no author distinction and no `.id` vs `user.id` ambiguity to mishandle. The parsing is a single boolean count: `sum(1 for t in threads if not t.get("isResolved"))`. Any future comment-id parsing would be net-new and would face the `.id`-vs-`user.id` risk the question anticipates — but it is not present today.

**Evidence:**

```
def unresolved_thread_count(review_threads):
    return sum(1 for t in (review_threads or []) if not t.get("isResolved"))
```

— `scripts/qrspi_pr_state.py:46-49`

```
reviewThreads(first:100) { nodes { isResolved } }
```

— `scripts/qrspi_pr_state.py:36` (no `comments`, no `id`, no `author` selected)

**Dependencies:** None beyond the GraphQL shape.
**Implicit contracts:** Threads are an opaque count today. Introducing comment ids/authors requires expanding `reviewThreads` to `{ id isResolved comments(first:N){ nodes { id databaseId body author{login} } } }` and being careful that `.id` (the GraphQL node id / `databaseId` the REST replies endpoint needs) is read, not the nested `author`/`user` id.

## Q10: What happens in the resolver when a PR is simultaneously APPROVED and carries an unaddressed reviewer comment — does any existing branch treat APPROVED as terminal in a way that would suppress a comment-response action?

**Answer:** APPROVED is NOT a hard terminal — `unresolvedThreads` gates BEFORE the APPROVED check. For a design/plan active phase, the order is: `submit` (no PR) → **`wait` if `unresolvedThreads > 0`** → `wait` if not APPROVED → `advance` if APPROVED+clean. So an APPROVED PR with unresolved THREADS returns `wait` (a unit test pins exactly this: "design PR approved but with unresolved threads -> wait"). BUT note the critical gap: the resolver only sees `unresolvedThreads` (a count of UNRESOLVED review THREADS), NOT plain unaddressed COMMENTS. A reviewer comment that does not open/leave an unresolved thread is invisible — an APPROVED PR with such a comment would fall straight through to `advance`/`land`. For implementation, APPROVED+clean slices → `land` (terminal merge). So APPROVED is effectively terminal for any reviewer comment that is NOT represented as an unresolved review thread; a comment-response feature could not rely on the existing `unresolvedThreads` signal to detect those.

**Evidence:**

```
if pr.get("unresolvedThreads", 0) > 0:
    return decision("wait", ...)
if pr.get("reviewDecision") != "APPROVED":
    return decision("wait", ...)
nxt = PHASES[_order(active) + 1]
return decision("advance", ...)
```

— `scripts/qrspi_resolve_state.py:134-150`

```
case("design PR approved but with unresolved threads -> wait (threads can't be auto-resolved)",
     state(phases={"design": _phase(decision="APPROVED", threads=2)}),
     {"action": "wait", "phase": "design"})
```

— `scripts/qrspi_resolve_state_test.py:70-72`

**Dependencies:** Pure resolver; depends on `qrspi_pr_state` populating `unresolvedThreads`.
**Implicit contracts:** "Unaddressed reviewer comment" is ONLY observable to the resolver if it surfaces as an unresolved review THREAD. Top-level conversation comments and resolved-thread comments are invisible. APPROVED+`unresolvedThreads==0` is terminal (advance/land), which WOULD suppress a comment-response for any comment not modeled as an unresolved thread.

## Q11: How does the existing revise path (`scripts/qrspi_revise_amend.py`) terminate and avoid re-triggering on subsequent runs, and what distinguishes that termination signal from a comment-reply that must NOT resolve or close the thread?

**Answer:** `qrspi_revise_amend.py` only stages+amends the phase commit (with a verification gate); termination is NOT in this script — it is the subsequent `gt submit --rerequest-review` (run by the worker per the SKILL/`doRevise`) flipping `reviewDecision` from CHANGES_REQUESTED back to REVIEW_REQUIRED. On the NEXT batch run, `qrspi_pr_state` re-gathers and sees REVIEW_REQUIRED (not CHANGES_REQUESTED), so `resolve()` no longer matches the reset/revise branch and returns `wait` — loop-safe termination via an observable state flip. The amend script's own guard (`verify_amend`) deliberately does NOT compare OIDs (timestamps bump them) and instead asserts "something was staged and tree is clean." The KEY distinction the ticket-shape implies: a comment-reply does NOT flip `reviewDecision` and does NOT resolve the thread (`isResolved` stays false, and the harness must NOT resolve it — thread resolution is the reviewer's job). So a comment-reply has NO equivalent built-in termination signal: replying again would re-fire unless a NEW idempotency mechanism (which does not exist today — Q7) records that the comment was already answered. This is the core design tension: revise terminates on a `reviewDecision` flip the agent can cause; a comment-reply terminates on neither a decision flip nor a thread-resolve, so re-trigger avoidance must come from elsewhere.

**Evidence:**

```
# Re-requesting flips reviewDecision back to REVIEW_REQUIRED, so the next pass
# resolves to `wait` instead of re-firing — that decision flip is the loop-safe
# termination signal, because review THREADS cannot be resolved here ...
```

— `.claude/workflows/qrspi-batch.js:40-45`

```
def verify_amend(staged, dirty):
    # NOTE: we deliberately do NOT compare commit OIDs — `gt modify` bumps the
    # committer timestamp ... "Were there staged changes" is the timestamp-independent truth.
    if not staged: return False, ("no staged changes at amend time ...")
    if dirty: return False, ("amend did not capture all edits ...")
    return True, None
```

— `scripts/qrspi_revise_amend.py:109-140`

**Dependencies:** `gt checkout`/`gt modify` (amend); the termination depends on the worker's later `gt submit --rerequest-review`.
**Implicit contracts:** Loop-safe automation requires a re-derivable state flip the agent can cause and the next gather can observe. Revise has one (`reviewDecision`); a thread/comment reply has none (the harness must not resolve threads, and a reply changes no gathered field), so a comment-response action needs a brand-new termination/idempotency primitive.

## Q12: How does the batch loop behave when a single PR has multiple unaddressed reviewer comments across different inline threads and the top level — does the current per-ticket single-action model accommodate multiple targeted replies in one run?

**Answer:** **No.** The model is strictly ONE autonomous action per ticket per run: `resolve()` returns a single `decision`, and the loop dispatches exactly one `do<Action>` handler, after which the ticket lands in a review-wait state. Multiple unresolved threads collapse to a single integer `unresolvedThreads` and a single `wait` decision — there is no per-thread or per-comment iteration anywhere in the resolver or batch. The closest existing multi-target pattern is `doRevise` for IMPLEMENTATION, which addresses EVERY CHANGES_REQUESTED slice branch "lowest slice number first" — but that loops over BRANCHES, not over comments/threads within one PR, and it is driven by the worker agent reading the PRs, not by structured per-comment data from the resolver. So multiple targeted replies in one run would require either (a) a new action whose worker iterates threads internally, or (b) the resolver emitting a list of comment/thread targets — neither exists today.

**Evidence:**

```
let res
switch (a) {
  case 'run_design': res = await doDesign(t, r); break
  ...
}
results.push(res)
processed.add(t.id)
```

— `.claude/workflows/qrspi-batch.js:848-867` (one action, then move on)

```
// Per run, each ticket advances at most ONE autonomous step (each step lands the
// ticket in a review-wait state).
```

— `.claude/workflows/qrspi-batch.js:36-37`

**Dependencies:** `resolve()` single-decision output; the sequential per-ticket loop.
**Implicit contracts:** One ticket → one action → review-wait. Per-comment/per-thread fan-out is not represented; the only intra-action multiplicity is `doRevise`'s per-slice-branch loop and `doImplementation`'s per-slice loop, both branch-keyed, not comment-keyed.

## Q13: What patterns do the existing stdlib-only `_test.py` siblings use to assert resolver classifications, and how are PR GraphQL/REST responses faked in those tests?

**Answer:** Two patterns. **`qrspi_resolve_state_test.py`** uses table-driven cases: helper builders `_phase(branch, pr, decision, threads)`, `_impl(slices, expected, pr_summary)`, `_slice(n, pr, decision, threads)`, and `state(assigned, linear, phases)` construct ALREADY-NORMALIZED state dicts (the resolver is pure, so no GraphQL is faked — tests feed the post-gather shape directly). `case(name, st, expect)` appends to a `CASES` list; `run()` asserts each `expect` key matches `resolve(st)`. **`qrspi_pr_state_test.py`** asserts the PARSERS directly with literal GraphQL-node dicts: it builds `nodes` lists shaped like `gh`'s `pullRequests.nodes` (e.g. `{"number":52, "reviewDecision":"APPROVED", "state":"OPEN", "reviewThreads":{"nodes":[{"isResolved":True}]}}`) and checks `parse_pr_nodes`/`select_pr`/`stack_merge_state` output via a `check(name, got, want)` helper. The subprocess/`gh` calls themselves are NOT tested ("the subprocess calls are not" — docstring). No HTTP/REST is mocked; the seam is the pure parser boundary.

**Evidence:**

```
def _phase(branch=True, pr=True, decision="REVIEW_REQUIRED", threads=0):
    return {"branchExists": branch, "prExists": pr,
            "reviewDecision": decision, "unresolvedThreads": threads}
...
case("design PR under review, no threads -> wait",
     state(phases={"design": _phase(decision="REVIEW_REQUIRED")}),
     {"action": "wait", "phase": "design"})
```

— `scripts/qrspi_resolve_state_test.py:14-65`

```
check("approved, all threads resolved",
      parse_pr_nodes([{"number": 52, "reviewDecision": "APPROVED", "state": "OPEN",
                       "reviewThreads": {"nodes": [{"isResolved": True}]}}]),
      {"prExists": True, "number": 52, ...})
```

— `scripts/qrspi_pr_state_test.py:61-65`

**Dependencies:** stdlib only (`assert`/manual `check`/`unittest` in revise-amend test). Run with `python3 scripts/<file>_test.py`.
**Implicit contracts:** Tests target PURE functions only; subprocess/`gh`/`git` seams are excluded by design (verified by manual e2e per CLAUDE.md). New comment-parsing logic must be factored as a pure function fed literal GraphQL/REST node dicts to be testable in this style.

## Q14: How is comment-author attribution and idempotency currently exercised in tests, if at all, and what fixtures exist for review threads and comment payloads?

**Answer:** **Not at all.** No test asserts comment authorship or reply idempotency, because no such code exists (Q6, Q7, Q9). The only review-thread "fixtures" are minimal `{"isResolved": bool}` node lists fed to `unresolved_thread_count`/`parse_pr_nodes` — they carry NO `id`, `author`, `user`, `body`, or `comments` fields. There are no comment-payload fixtures anywhere. The richest PR fixtures are the `stack_merge_state` node builders (`_node`/`_nodes` with `number`/`state`/`merged`/`reviewDecision`/`reviewThreads`) used for merge-awareness tests — still no comment data. So a comment-response feature would introduce the FIRST author/idempotency tests and the FIRST comment-payload fixtures in this codebase.

**Evidence:**

```
check("mixed -> count unresolved",
      unresolved_thread_count([{"isResolved": True}, {"isResolved": False},
                               {"isResolved": False}]), 2)
```

— `scripts/qrspi_pr_state_test.py:49-51` (the only review-thread fixtures; no author/id/body)

```
def _node(number, state, merged):
    return [{"number": number, "state": state, "merged": merged,
             "reviewDecision": "APPROVED", "reviewThreads": {"nodes": []}}]
```

— `scripts/qrspi_pr_state_test.py:202-204`

**Dependencies:** None.
**Implicit contracts:** Existing fixtures model threads as opaque resolved/unresolved booleans. Author attribution and reply idempotency are entirely untested ground.

## Q15: How does the batch workflow currently surface its per-ticket action decisions and skips, so a new comment-response action and any decline-with-rationale outcome would be visible in run output?

**Answer:** Via `log(...)` calls and a structured `results[]` array returned at the end. Per ticket the loop logs the decision (`${t.id}: decision=${a} — ${r.decision.reason}`) and the outcome (`${t.id} → ${res.action} (${res.newStatus})`). Skips are logged explicitly (`skipped (${a})`) and recorded via `skip(t, decision, note)` → `{ticketId, action, summary}`. Failures use `failTicket`/`finResult`/`resolve_failed`/`restack_conflict`/`errored` records, each with a `summary`. The final return is `{ ticketsProcessed, results, reconciliation }`. A new comment-response action would surface by (1) adding its `case` log line, (2) returning a result object with `action` + `summary` (and a `prUrl`/decline rationale in `summary`); a decline-with-rationale would naturally fit the existing `{action, summary}` shape exactly as `wait`/`skip` do today.

**Evidence:**

```
const a = r.decision.action
log(`  ${t.id}: decision=${a} — ${r.decision.reason}`)
...
results.push(res)
processed.add(t.id)
log(`[${i + 1}/${tickets.length}] ${t.id} → ${res.action}${res.newStatus ? ` (${res.newStatus})` : ''}`)
```

— `.claude/workflows/qrspi-batch.js:846-868`

```
function skip(t, decision, note) {
  return { ticketId: t.id, action: decision.action, summary: note }
}
```

— `.claude/workflows/qrspi-batch.js:243-245`

**Dependencies:** `log()` and `phase()` (workflow runner primitives); the returned `results[]`.
**Implicit contracts:** Every per-ticket outcome is BOTH logged AND pushed as a `{ticketId, action, summary, newStatus?, prUrl?}` record. A new action must return that shape to remain visible. The `wait`/`skip` precedent already models a "nothing-done, here's why" outcome — a decline-with-rationale maps onto it directly.

---

## Discovered Patterns

- **Self-locating one-shot scripts as the path-mangling antidote.** Every git/gh-mutating step a weak worker would otherwise hand-type is wrapped in a `scripts/qrspi_*.py` that derives `REPO_ROOT` from `__file__` (or `git --git-common-dir`), takes only short token args (`--ticket`, `--slice`, `--branch`), and prints a single JSON envelope `{ok, ..., error?}`. Examples: `qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_pr_body.py`, `qrspi_revise_amend.py`, `qrspi_restack.py`, `qrspi_cleanup.py`. A new comment-reply helper would follow this exact mold.
- **Pure-core / impure-shell split for testability.** Each script separates pure parsers (unit-tested with literal dicts) from subprocess-backed mechanics (untested, verified by manual e2e). Tests are stdlib-only, table-driven (`case`/`check`), run via `python3 scripts/<x>_test.py`.
- **Text-return + JS-parse, never StructuredOutput, for the weak local worker.** Workers echo the script's JSON stdout verbatim; the JS orchestrator re-parses with `extractJsonObject` + `parse*Envelope` (the StructuredOutput tool path stalled the qwen worker). Any new envelope-producing worker must follow this.
- **State is re-derived, never persisted, for idempotency.** The resolver recomputes the single action from live PR/git state each run; loops terminate on observable state flips (e.g. `reviewDecision` CHANGES_REQUESTED→REVIEW_REQUIRED), not on stored ledgers.
- **All authenticated gh PR writes are forbidden in code; only `gt submit` (Graphite App credential) writes the PR** (reviewers at creation, body at creation, rerequest-review). Reads via `gh`/`gh api graphql` are fine.
- **One ticket → one autonomous action per run.** The only intra-action multiplicity is branch-keyed (per-slice in `doImplementation`/`doRevise`), never comment- or thread-keyed.

## Inconsistencies

- **MEMORY says gh PR writes WORK; all repo code/docs say they 403.** Global project MEMORY records "gh PR writes NOW WORK (classic PAT) … RESOLVED 2026-06-08 … unblocks RUS-54." But EVERY in-repo assertion — `qrspi_resolve_state.py:31-33,136-139`, `qrspi-batch.js:42-47,606-614`, `qrspi-work/SKILL.md:300-303,352-358` — still states that all authenticated gh PR-write mutations 403 on this cross-owned repo, and the resolver routes thread-only PRs to `wait` SPECIFICALLY because of that 403. No code reflects the resolution. This is the central code-vs-fact gap relevant to any comment-reply feature: the in-repo invariant "we cannot write PR comments/threads" may no longer hold per MEMORY, but nothing in the codebase has been updated to act on it.
- **`unresolvedThreads` is the only comment signal, but it models THREADS, not COMMENTS.** The resolver/batch language frequently says "reviewer comment(s)" (e.g. `qrspi_resolve_state.py:185`), yet the only gathered datum is a count of unresolved review THREADS (`isResolved` booleans). Top-level conversation comments and individual comment authors/bodies are never gathered, so "unaddressed reviewer comment" and "unresolved review thread" are conflated in prose while the code only sees the latter.
- **Linear `save_comment` vs GitHub PR comment.** `mcp__linear__save_comment` is an allowed tool in `qrspi-work/SKILL.md:6` (writes Linear issue comments), which can be mistaken for a GitHub PR comment-write capability — it is unrelated to PR review threads.
- **Co-Authored-By trailer model drift.** The SKILL revise example commits `Co-Authored-By: Claude Opus 4.7 (1M context)` (`SKILL.md:343`) while the slice-commit worker prompt in `qrspi-batch.js:521` says to append "the Co-Authored-By trailer" generically; the global commit convention is `Claude Opus 4.8`. Cosmetic, but a comment-reply body author trailer would need a single source of truth.
