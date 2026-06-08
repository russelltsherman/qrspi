# Design — Batch addresses reviewer comments on in-review PRs, not just change requests

**Ticket:** RUS-54
**Research basis:** research.md @ 2026-06-08T00:00:00Z
**Generated:** 2026-06-08T00:00:00Z
**Status:** revised (review questions resolved — see Resolved Questions)

## Current State

The PR-gated batch resolves one autonomous action per ticket per run from live PR/git state; idempotency comes from re-deriving state, never persisted ledgers, with loops terminating on observable state flips like `reviewDecision` CHANGES_REQUESTED → REVIEW_REQUIRED (ref: Q4, Q7, Q11).

PR review state is gathered by a single read-only GraphQL `PR_QUERY` in `qrspi_pr_state._query_pr()` that, per head ref, fetches `number`, `state`, `merged`, `mergedAt`, `reviewDecision`, and `reviewThreads(first:100){ nodes { isResolved } }` — only the boolean `isResolved` per thread (ref: Q1). `parse_pr_nodes()` reduces all threads to one integer `unresolvedThreads` via `unresolved_thread_count()`; no comment `id`, `author`, `body`, `path`, `databaseId`, or `in_reply_to` is fetched anywhere (ref: Q1, Q9). Consequently there is no author-attribution logic and no `.id`-vs-`user.id` ambiguity to mishandle today — comment-level data is entirely absent (ref: Q9).

The state envelope from `qrspi_resolve.py` (`build_envelope()`) carries `{ok, repoRoot, worktreeDir, existing, decision, reviewers, teamReviewers, ticketContent}`; the raw gathered `state` (including `phases.<name>` with `reviewDecision`/`unresolvedThreads`/`number`) is consumed to compute `decision` but is NOT re-emitted, so the envelope is the sole script→orchestrator channel and per-comment data has nowhere to flow today (ref: Q2).

The pure resolver `resolve(state)` is a strict priority cascade: entry gate → reset/revise on the lowest CHANGES_REQUESTED phase → active-phase handling where `submit` (no PR) precedes `wait` (if `unresolvedThreads > 0`) precedes `wait` (if not APPROVED) precedes `advance`/`land` (ref: Q4, Q8). A thread-only PR (unresolved threads, no formal CR) is the explicit terminal-for-automation `wait` sink, chosen because GitHub thread mutations were believed to 403 on this cross-owned repo so an autonomous revise could never clear the gate (ref: Q4, Q8). APPROVED is not a hard terminal — `unresolvedThreads` gates before the APPROVED check, so an APPROVED-with-unresolved-threads PR returns `wait` — but a reviewer comment that is NOT an unresolved review thread (a top-level comment, or a comment on a resolved thread) is invisible and falls straight through to `advance`/`land` (ref: Q10).

There is NO comment-write path anywhere in the codebase; the only gh mutation surface forbidden by every in-repo assertion, with the only working PR write being Graphite's GitHub-App credential at `gt submit` (reviewers/body at creation, rerequest-review) (ref: Q5). There is NO comment/thread idempotency state of any kind — `.qrspi/<id>/` holds only phase artifacts, no per-comment marker (ref: Q7). Reviewer identity resolution exists only as "who to request review FROM" (`load_reviewers()`, `@me` → `_gh_authenticated_login()`); there is no bot-identity constant and no "who AUTHORED a comment" logic (ref: Q6). The batch dispatches exactly one `do<Action>(t, r)` per ticket via `switch (r.decision.action)`; multiplicity exists only branch-keyed (per-slice in `doImplementation`/`doRevise`), never comment- or thread-keyed (ref: Q3, Q12). Every outcome is both logged and pushed as a `{ticketId, action, summary, newStatus?, prUrl?}` record; a decline-with-rationale maps directly onto the existing `wait`/`skip` "nothing-done, here's why" shape (ref: Q15). Resolver/parser tests are stdlib-only and table-driven, feeding literal already-normalized state dicts (resolver) or literal GraphQL node dicts (parsers); subprocess/gh/git seams are untested by design, and no comment-payload fixtures or author/idempotency tests exist (ref: Q13, Q14).

A central inconsistency: global MEMORY records gh PR comment writes as RESOLVED 2026-06-08 (bot on a classic PAT; in-thread reply path verified end-to-end), and the ticket constraints confirm the inline-reply path works — yet every in-repo assertion still says gh PR writes 403, and the resolver routes thread-only PRs to `wait` specifically because of that stale belief (ref: Q5, Q11).

## Desired End State

- **AC1** — The gather fetches per-comment data on in-review PRs; the resolver, after the reset/revise check and before the `wait` sinks, detects at least one unaddressed reviewer-authored comment and emits a new `respond_comment` action, even with no CHANGES_REQUESTED and even when APPROVED (the new detection runs independent of, and ahead of, the APPROVED-terminal path that today suppresses non-thread comments) (ref: Q8, Q10).
- **AC2** — The `respond_comment` worker receives the comment body/context and answers questions faithfully from the actual state of the work, following the honesty directive (no fabricated claims).
- **AC3** — For a suggested change the worker either applies it to the relevant code/artifacts (when judged sound) or declines, and in both cases records a written rationale — applied changes amend the phase commit via the existing self-locating amend mechanism; the rationale lands in the reviewer's thread reply (the in-thread reply alone satisfies this obligation, no artifact/impl-log duplication — see RQ5).
- **AC4** — The worker declines and explains, rather than complying, when a change is incorrect, unworkable, or violates safety/security guidelines — it acts as a reviewer's peer, not an order-taker.
- **AC5** — A comment already responded to does not retrigger on a later run; the agent's own bot-authored comments are never treated as reviewer input (the detector filters by author and by an in-thread reply marker the next gather observes).
- **AC6** — Detection attributes each comment to its author by reading the comment `.id`/`databaseId` and `author.login` from the API response field (not a regex over the JSON blob, which would grab the nested `user.id`), so the agent never responds to or loops on its own replies (ref: Q6, Q9).
- **AC7** — The response lands in the reviewer's own thread: an inline comment is answered by a reply inside that same inline review thread via `POST /repos/{owner}/{repo}/pulls/{n}/comments/{comment_id}/replies`; a top-level conversation comment is answered at top level. Responses never go via commit messages or the PR body (ref: Q5).
- **Out of scope (unchanged):** formal CHANGES_REQUESTED reset/revise behavior; auto-resolving/closing threads (replying ≠ resolving); approval/advancement computation (ref: Q4, Q8, Q11).

## Delta

- **`scripts/qrspi_pr_state.py` (modified)** — Expand `reviewThreads` in `PR_QUERY` to `{ id isResolved comments(first:N){ nodes { databaseId body author{login} } } }` and add top-level `comments(first:N){ nodes { databaseId body author{login} } }`. Add a pure function that, given the authenticated/bot login, returns the list of unaddressed reviewer-authored comments per phase: `{commentId (databaseId), author, body, threadType (inline|toplevel), threadId, lastReplyAuthor}`. Carry this list into `phases.<name>` alongside `unresolvedThreads`.
- **`scripts/qrspi_resolve_state.py` (modified)** — Insert a `respond_comment` branch after the reset/revise check and ahead of the `wait`/APPROVED sinks: if a phase carries ≥1 unaddressed reviewer comment, return `respond_comment` with the phase and a comment-target list. Add `respond_comment` to the action vocabulary.
- **`scripts/qrspi_resolve.py` (modified)** — Pass the authenticated login into the gather (reusing `_gh_authenticated_login()`), and re-emit the per-phase comment targets in the envelope (a new field, e.g. `commentTargets`, since `decision` keys are fixed and the raw state is dropped today) (ref: Q2, Q6).
- **`scripts/qrspi_comment_reply.py` (new, self-locating)** — Take `--ticket`, `--pr`, `--comment-id`, `--reply-mode` (inline|toplevel), `--body-file`; perform the gh REST write (inline: `.../comments/{id}/replies`; top-level: `gh pr comment`); capture the new reply's `.id` from the API response; print a JSON envelope `{ok, replyId, inReplyToId, error?}` (ref: Q5).
- **`.claude/workflows/qrspi-batch.js` (modified)** — Add `respond_comment` to `RESOLVE_ACTIONS`, a `case` in the dispatch `switch`, and a `doRespondComment(t, r)` handler that iterates `r.commentTargets` (the only comment-keyed multiplicity in the harness), builds a peer-reviewer worker prompt per comment, invokes the reply script, optionally amends on applied changes, logs, and returns `{ticketId, action, summary, prUrl}` (ref: Q3, Q12, Q15).
- **`.claude/agents/qrspi-*` (extend the existing revise worker — see RQ4)** — Extend the existing revise worker (not a new agent) so it engages substantively: answer / apply / decline-with-rationale, honesty-bound, reusing the same self-locating amend mechanism for applied changes.
- **Tests (new)** — `qrspi_pr_state_test.py`: first comment-payload fixtures + author-attribution + `databaseId`-vs-`user.id` assertions. `qrspi_resolve_state_test.py`: `respond_comment` precedence cases (after CR, before `wait`, fires even when APPROVED; no fire when only bot replies remain) (ref: Q13, Q14).
- **Docs (modified)** — Update the stale "gh PR writes 403" assertions in CLAUDE.md / qrspi-batch.js / SKILL.md that the `wait`-for-threads rationale rests on (ref: Q5, Q11, Inconsistencies).

## Pattern Decisions

### Decision 1: Idempotency / re-trigger avoidance for a comment reply

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Re-derive from PR state: a reviewer comment is "unaddressed" iff there is no later reply authored by the bot login in that same thread (inline: `in_reply_to_id` chain; top-level: a later bot comment) | Matches the codebase's "state is re-derived, never persisted" invariant (ref: Q7); no new ledger; survives re-runs and worktree wipes; the bot reply IS the observable termination signal | Requires fetching comment authors + reply chains correctly; top-level "addressed" is heuristic (no thread structure) |
| B | Persisted ledger: a `comment-replies.json` under `.qrspi/<id>/` recording replied comment ids | Explicit, simple to reason about | Net-new convention against the grain (ref: Q7); the marker can desync from PR truth; not in `ARTIFACTS`; another path-sensitive write |

**Recommendation:** Option A
**Rationale:** The harness deliberately achieves idempotency by recomputing the action from live state and terminating on an observable flip (`reviewDecision` for revise), never on stored ledgers (ref: Q4, Q7, Q11). A bot-authored reply in the thread is exactly such an observable flip — the next gather sees it and the comment is no longer "unaddressed." This reuses the existing idempotency philosophy rather than introducing the first persisted ledger.
**NEW PATTERN?** No — it extends the existing "re-derive + terminate on observable flip" pattern to a new observable (a bot reply in-thread), which substitutes for the `reviewDecision` flip that a comment reply cannot cause (ref: Q11).

### Decision 2: Author attribution / bot-vs-reviewer discrimination

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Resolve the bot login from `gh api user -q .login` (reuse `_gh_authenticated_login()`); filter comments where `author.login == bot` out of the "reviewer" set; read ids from `.databaseId`/`.id` API fields | Reuses existing `@me`→login resolution (ref: Q6); portable (no hard-coded `russelltshermanbot`); avoids the `.id`-vs-`user.id` regex trap by reading the field | Bot identity = authenticated identity (true today; an assumption to document) |
| B | Hard-code a bot-login constant (`russelltshermanbot`) | Simplest | Breaks portability/shareability; `russelltshermanbot` lives only in MEMORY, not repo code (ref: Q6); contradicts the no-hard-coded-identity convention |

**Recommendation:** Option A
**Rationale:** `qrspi_resolve.py` already resolves the authenticated login for `@me` expansion (ref: Q6); the same login is the bot author for filtering. Reading `.databaseId`/`.id` from the parsed API response (not a JSON-blob regex) directly satisfies AC6's anti-loop requirement and the ticket constraint to capture ids from `.id`, not the nested `user.id` (ref: Q9).
**NEW PATTERN?** Yes (minor) — first author-attribution logic in the codebase (none exists today, ref: Q6, Q9); justified because no existing pattern distinguishes comment authors, and the feature cannot avoid loops (AC5/AC6) without it. It reuses the existing login-resolution helper rather than inventing identity resolution wholesale.

### Decision 3: Comment-write mechanism

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | New self-locating `scripts/qrspi_comment_reply.py` doing the gh REST write, pure-core/impure-shell, JSON envelope | Matches every existing mutating helper (`qrspi_persist.py`, `qrspi_revise_amend.py`, ref: Discovered Patterns); testable pure core; weak-worker-safe one-shot invocation | Net-new script + the first in-repo gh PR write (a forbidden surface until 2026-06-08) |
| B | Inline the gh calls in the `doRespondComment` JS handler | Fewer files | Path/quoting-sensitive for the weak worker; no pure-core test seam; breaks the self-locating-script convention (ref: Discovered Patterns) |

**Recommendation:** Option A
**Rationale:** Every git/gh-mutating step a weak worker would hand-type is wrapped in a self-locating `scripts/qrspi_*.py` returning a JSON envelope; a comment-reply helper follows this exact mold (ref: Q5, Discovered Patterns). The inline-reply path (`POST .../comments/{id}/replies`) and top-level `gh pr comment` are the verified mechanisms (ticket constraints).
**NEW PATTERN?** No (structurally) — it is the established self-locating-script pattern; it does newly exercise a gh PR-write surface, which depends on the MEMORY-recorded 403 resolution being real (see Risk Register).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| gh PR comment writes still 403 in this environment despite MEMORY's "RESOLVED" note (code-vs-fact gap, ref: Q5, Inconsistencies) | med | high | Re-verify the inline-reply + top-level write end-to-end in this environment BEFORE shipping detection (the verification gate the ticket cites); if it fails, the whole feature is blocked and the `wait` sink stays correct |
| Reply loop: bot replies to its own reply, or re-replies each run (violates AC5/AC6) | med | high | Author-filter by resolved bot login (Decision 2) + re-derive "unaddressed" from the in-thread bot reply (Decision 1); add explicit tests for "bot reply present → no re-fire" and "`.databaseId` not `user.id`" |
| Top-level comments have no thread structure, so "already addressed" is heuristic and may mis-detect | med | med | Define a deterministic rule (a later top-level bot comment after the reviewer's comment timestamp marks it addressed); cover with fixtures; accept that top-level idempotency is coarser than inline |
| `respond_comment` mis-prioritized — masks a formal CR, or fires on APPROVED PRs that should advance | low | high | Slot strictly AFTER the reset/revise check and gate on reviewer-authored unaddressed comments only; pin precedence with resolver tests ("CR outranks respond_comment", "respond_comment outranks wait", ref: Q8) |
| Multiple comments across threads in one run exceed the one-action-per-ticket model (ref: Q12) | med | med | Make `doRespondComment` iterate `r.commentTargets` internally (comment-keyed multiplicity, analogous to `doRevise`'s branch loop); each reply is independent and idempotent, so a partial run self-heals next pass |
| Worker over-complies (applies an unsound or unsafe change) violating AC4 | low | high | Peer-reviewer worker prompt enforces the honesty/decline-with-rationale directive; applied changes go through the existing amend+verify gate, never a blind write |

## Resolved Questions

All five questions below were raised in design review and resolved by the reviewer (PR #165,
inline comments on this section). The reviewer's decisions are now folded into the design above:

- **RQ1 (was OQ1): Is the gh PR-write 403 genuinely resolved in THIS runtime?**
  **Resolved: yes — it is resolved.** The reviewer confirms the gh PR-write 403 is genuinely
  resolved in this runtime (the bot is on a classic PAT; the in-thread inline-reply path is
  verified end-to-end, consistent with the MEMORY "RESOLVED 2026-06-08" note). The feature is
  therefore unblocked: the comment-write path (Decision 3 / `qrspi_comment_reply.py`) and the
  `respond_comment` action proceed. The "still 403" entry in the Risk Register stays only as a
  guard to re-verify before shipping, but it is no longer an open blocker, and the stale
  in-repo "gh PR writes 403" assertions are corrected per the Delta's Docs item.

- **RQ2 (was OQ2): What exact rule marks a top-level conversation comment "addressed"?**
  **Resolved: a reply answering the question / responding to the concern marks it addressed.**
  A top-level reviewer comment is "addressed" once the bot has posted a later reply that
  answers the question or responds to the concern (a later bot top-level comment after the
  reviewer's comment timestamp), per Decision 1 / AC5. No explicit reply-reference convention is
  required beyond authorship + ordering; this is the deterministic top-level rule the Risk
  Register row already names.

- **RQ3 (was OQ3): Should `respond_comment` fire on resolved-thread / pre-approval comments, or only the `wait`/APPROVED-suppressed cases?**
  **Resolved: only on the `wait`/APPROVED-suppressed cases (ref: Q10).** `respond_comment` fires
  exactly for the cases the ticket calls out — reviewer comments that would otherwise be
  swallowed by the `wait`/APPROVED terminal paths — not on already-resolved threads or
  pre-approval comments. This keeps the new action narrowly scoped and preserves the resolver
  precedence pinned in AC1 and the Risk Register (CR outranks `respond_comment`; `respond_comment`
  outranks `wait`).

- **RQ4 (was OQ4): New `qrspi-respond-comment` agent, or extend the existing revise worker?**
  **Resolved: extend the existing revise worker.** The response worker is an extension of the
  existing revise worker rather than a brand-new agent, since both edit artifacts/code and amend
  the phase commit via the same self-locating amend mechanism. The Delta item
  "`.claude/agents/qrspi-*` (new respond-comment worker, **or extend revise**)" resolves to the
  extend-revise option.

- **RQ5 (was OQ5): On a DECLINE, is the in-thread reply alone sufficient for AC3's rationale?**
  **Resolved: the in-thread reply alone is sufficient.** When the worker declines a change, the
  recorded rationale required by AC3 lives in the reviewer's in-thread reply; no additional
  duplication into the phase artifact or impl-log is required. AC3's "the rationale lands in the
  reviewer's thread reply" is the complete obligation.
