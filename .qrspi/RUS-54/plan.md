# Implementation Plan — Batch addresses reviewer comments on in-review PRs, not just change requests

**Structure basis:** structure.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft
**Total steps:** 38

## Plan-phase decisions (resolving structure's Unverified Assumptions)

- **Comment page size N = 100.** Match the existing `reviewThreads(first:100)` cap in `PR_QUERY`. Both the per-thread inline `comments(first:100)` and the top-level `comments(first:100)` use 100; pagination beyond 100 is out of scope (a comment chain >100 deep is not a realistic review surface and would only cause a re-fire, never a wrong write).
- **Ordering field = `createdAt`.** Fetch `createdAt` on every comment node (inline and top-level) and order top-level "addressed" detection by `createdAt` ascending, not raw node-array order, so the deterministic "a later bot top-level comment after the reviewer's comment" rule (RQ2) has a stable key.
- **Exact agent/skill file paths** (the revise worker `.claude/agents/qrspi-*` and the `SKILL.md` carrying the stale 403 text) are left to the WorkTree phase to resolve by codebase read; this plan references them by their structure-named glob and the grep that locates them.

## Slice 1: Comment gather + resolver detection (pure Python core)

### Setup

1. ⚠️ Modify `scripts/qrspi_pr_state.py` — expand the `reviewThreads` selection inside `PR_QUERY` to fetch per-comment data.
   - **Current:** `reviewThreads(first:100){ nodes { isResolved } }`
   - **After:** `reviewThreads(first:100){ nodes { id isResolved comments(first:100){ nodes { databaseId body createdAt author{login} } } } }`

2. ⚠️ Modify `scripts/qrspi_pr_state.py` — add a top-level `comments` selection to `PR_QUERY` (the PR node, alongside `reviewDecision`/`reviewThreads`).
   - **Current:** PR node selects `number state merged mergedAt reviewDecision reviewThreads(...)`
   - **After:** also selects `comments(first:100){ nodes { databaseId body createdAt author{login} } }`

### Core Logic

3. ✨ Add pure function `unaddressed_reviewer_comments(pr_node: dict, bot_login: str) -> list[dict]` in `scripts/qrspi_pr_state.py` — returns reviewer-authored `CommentTarget` dicts `{commentId, author, body, threadType, threadId, lastReplyAuthor}` with no later bot reply in-thread. Reads ids from `.databaseId` and author from `author.login` (never a JSON-blob regex). Filters out any comment where `author.login == bot_login`. Per structure Contracts and AC5/AC6.

4. ⚠️ Modify `scripts/qrspi_pr_state.py` — in `unaddressed_reviewer_comments`, implement the inline rule: a reviewer comment in a `reviewThreads` thread is unaddressed iff no later comment in that same thread's `comments` chain has `author.login == bot_login`. Set `threadType="inline"`, `threadId` = the thread `id`, `lastReplyAuthor` = last comment's `author.login`.

5. ⚠️ Modify `scripts/qrspi_pr_state.py` — in `unaddressed_reviewer_comments`, implement the top-level rule: a top-level reviewer comment is unaddressed iff no bot-authored top-level comment has a strictly greater `createdAt`. Set `threadType="toplevel"`, `threadId=None`. Order both sets by `createdAt` ascending before comparison.

6. ⚠️ Modify `scripts/qrspi_pr_state.py` — change the parse path (`parse_pr_nodes()` / wherever `phases.<name>` is built) to accept the bot login and carry `commentTargets: list[CommentTarget]` into each `phases.<name>` dict, alongside the existing `unresolvedThreads`/`reviewDecision`/`number`.
   - **Current:** `phases.<name>` = `{number, reviewDecision, unresolvedThreads, ...}`
   - **After:** adds `commentTargets` (default `[]` when bot login unavailable or no comments)

7. ⚠️ Modify `scripts/qrspi_resolve_state.py` — add `"respond_comment"` to the action vocabulary (the set/tuple of legal action strings).

8. ⚠️ Modify `scripts/qrspi_resolve_state.py` — insert the `respond_comment` branch in `resolve(state)`.
   - **Current:** cascade is entry gate → reset/revise (lowest CHANGES_REQUESTED) → `submit` → `wait`(threads) → `wait`(not APPROVED) → `advance`/`land`
   - **After:** insert strictly AFTER the reset/revise check and AHEAD of the `wait`/APPROVED sinks: if a phase carries ≥1 `commentTargets`, return `{action: "respond_comment", phase, commentTargets}`. Fires even when APPROVED; CR still outranks it.

### Tests

9. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — add a fixture + test: an inline reviewer comment with no bot reply yields one `CommentTarget`; assert `commentId` comes from `.databaseId` (not a nested `user.id`), `author` from `author.login`, `threadType == "inline"`.

10. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — add a test: a bot reply present later in the same inline thread → that comment is NOT returned (idempotency / AC5).

11. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — add a test: a top-level reviewer comment with a later bot top-level comment (greater `createdAt`) → not returned; without one → returned with `threadType == "toplevel"`.

12. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — add a test: a comment authored by `bot_login` is always filtered out (never treated as reviewer input), proving author attribution.

13. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — add test: a phase with `commentTargets` AND `reviewDecision == CHANGES_REQUESTED` → resolver returns the reset/revise action, NOT `respond_comment` (CR outranks).

14. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — add test: a phase with `commentTargets` and unresolved threads / not-APPROVED → returns `respond_comment` (it outranks `wait`).

15. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — add test: a phase with `commentTargets` AND `reviewDecision == APPROVED` → returns `respond_comment` (fires when APPROVED).

16. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — add test: a phase whose comments are all bot replies (empty `commentTargets`) → does NOT return `respond_comment` (falls through to the normal sink).

17. Run: `python3 scripts/qrspi_pr_state_test.py`
    - **Expected:** all tests pass, including the four new gather fixtures.

18. Run: `python3 scripts/qrspi_resolve_state_test.py`
    - **Expected:** all tests pass, including the four precedence cases.

### Verify Slice 1

19. **Checkpoint:** `python3 scripts/qrspi_pr_state_test.py && python3 scripts/qrspi_resolve_state_test.py`
    - [ ] Both suites exit 0.
    - [ ] `unaddressed_reviewer_comments` reads `.databaseId`/`author.login` fields, never a regex over the JSON blob.
    - [ ] `respond_comment` is in the action vocabulary and slotted after reset/revise, before `wait`/APPROVED.

---

## Slice 2: Comment-reply write helper + gh-write re-verification gate

### Setup

20. ✨ Create `scripts/qrspi_comment_reply.py` — new self-locating CLI (pure-core / impure-shell), purpose: perform one inline or top-level reviewer-comment reply and print a `ReplyEnvelope` JSON. Self-locates the repo root from its own `__file__`, mirroring `qrspi_persist.py`/`qrspi_revise_amend.py`.

21. ⚠️ Modify `scripts/qrspi_comment_reply.py` — add argparse: `--ticket`, `--pr`, `--comment-id`, `--reply-mode {inline|toplevel}`, `--body-file`. Read the reply body from `--body-file` (avoids weak-worker quoting hazards).

### Core Logic

22. ✨ Add pure function `mode_to_request(reply_mode, owner, repo, pr, comment_id, body) -> dict` in `scripts/qrspi_comment_reply.py` — maps `inline` → `{"method":"POST","path":"/repos/{owner}/{repo}/pulls/{pr}/comments/{comment_id}/replies","fields":{"body":...}}` and `toplevel` → `{"tool":"gh","cmd":["pr","comment", ...]}`. Pure (no I/O), so it is unit-testable.

23. ✨ Add pure function `response_to_envelope(reply_mode, raw_response, in_reply_to_id) -> dict` in `scripts/qrspi_comment_reply.py` — parses the gh/REST response into `ReplyEnvelope {ok, replyId, inReplyToId, error}`, capturing the created reply's `.id`. Pure.

24. ⚠️ Modify `scripts/qrspi_comment_reply.py` — add the impure `main()`: resolve owner/repo (self-located), call `gh api` for inline replies or `gh pr comment` for top-level via subprocess, feed the result through `response_to_envelope`, and print the JSON envelope to stdout. On any subprocess failure, print `{ok:false, replyId:null, inReplyToId:..., error:<msg>}`.

### Tests

25. ✨ Create `scripts/qrspi_comment_reply_test.py` — stdlib-only, table-driven, purpose: unit-test the pure core (no subprocess/gh).

26. ⚠️ Modify `scripts/qrspi_comment_reply_test.py` — test `mode_to_request`: `inline` produces the `.../comments/{id}/replies` POST path with the body field; `toplevel` produces the `gh pr comment` form.

27. ⚠️ Modify `scripts/qrspi_comment_reply_test.py` — test `response_to_envelope`: a successful response yields `ok=true` with `replyId` from `.id` and the correct `inReplyToId`; a failure/exception path yields `ok=false` with a populated `error` and `replyId=null`.

28. Run: `python3 scripts/qrspi_comment_reply_test.py`
    - **Expected:** all pure-core tests pass.

### Verify Slice 2

29. **Checkpoint:** `python3 scripts/qrspi_comment_reply_test.py`
    - [ ] Pure-core suite exits 0.
    - [ ] Manual end-to-end (the design-mandated gh-write re-verification gate, Risk Register row 1): against a real test PR with the bot credential, run the script once with `--reply-mode inline` and once with `--reply-mode toplevel`; confirm both return `ok:true` (no 403) and the printed `replyId` matches the comment created on GitHub. If either 403s, STOP — the feature is blocked and Slice 3 must not rely on it; the `wait` sink stays correct.

---

## Slice 3: Envelope wiring, batch dispatch, and peer-reviewer worker

### Setup

30. ⚠️ Modify `scripts/qrspi_resolve.py` — pass the authenticated login (reuse `_gh_authenticated_login()`) into the gather call so `unaddressed_reviewer_comments` can filter by bot login.
    - **Current:** gather is invoked without a bot-login argument
    - **After:** gather receives `bot_login = _gh_authenticated_login()`

31. ⚠️ Modify `scripts/qrspi_resolve.py` — in `build_envelope()`, re-emit a top-level `commentTargets` field (per-phase comment-target list) in the envelope, since `decision` keys are fixed and the raw gathered state is dropped today.
    - **Current:** envelope = `{ok, repoRoot, worktreeDir, existing, decision, reviewers, teamReviewers, ticketContent}`
    - **After:** adds `commentTargets`

### Core Logic

32. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add `"respond_comment"` to the `RESOLVE_ACTIONS` set.

33. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add a `case "respond_comment":` to the dispatch `switch (r.decision.action)` that calls `doRespondComment(t, r)`.

34. ✨ Add `doRespondComment(t, r)` in `.claude/workflows/qrspi-batch.js` — iterates `r.commentTargets` (comment-keyed multiplicity, analogous to `doRevise`'s branch loop); per comment, builds a peer-reviewer worker prompt, writes the reply body to a staging file, invokes `scripts/qrspi_comment_reply.py`, amends the phase commit via the existing self-locating amend mechanism only when changes were applied, and returns `{ticketId, action, summary, prUrl}`.

35. ⚠️ Modify `.claude/agents/qrspi-*` (the existing revise worker definition — exact file resolved in WorkTree via `grep -rl "CHANGES_REQUESTED\|revise" .claude/agents/`) — extend it to engage each comment as a peer reviewer per AC2–AC4: answer faithfully from actual state (honesty-bound), apply+amend a sound change, or decline-with-rationale; the rationale lands in the in-thread reply (RQ5 — no artifact/impl-log duplication).

### Docs

36. ⚠️ Modify `.claude/CLAUDE.md` — correct the stale "gh PR writes 403" / `wait`-for-threads assertions in the Lifecycle and Codebase-conventions sections to reflect that gh PR comment writes succeed (classic PAT) and that thread-only PRs carrying reviewer comments are now handled by `respond_comment`.

37. ⚠️ Modify `.claude/skills/qrspi-*/SKILL.md` (the batch/revise skill wrapper — exact file resolved in WorkTree via `grep -rl "403" .claude/skills/`) — correct the stale 403 assertion. (Note: the `qrspi-batch.js` doc/comment strings are corrected in the same file edited at steps 32–34.)

### Verify Slice 3

38. **Checkpoint:** `node --check .claude/workflows/qrspi-batch.js`
    - [ ] `node --check` passes; `doRespondComment` is reachable via the dispatch switch and `RESOLVE_ACTIONS` includes `respond_comment`.
    - [ ] Manual end-to-end batch run against a PR with one unaddressed reviewer comment: the worker posts an in-thread reply; a second batch run does NOT re-respond (idempotency via the observed bot reply); a CR on the same PR still outranks `respond_comment`.
    - [ ] `grep -rn "gh PR writes 403\|every gh mutation 403s\|gh.*403" .claude/CLAUDE.md .claude/workflows/qrspi-batch.js .claude/skills/` returns no remaining stale 403 assertion across the three touched doc surfaces.

---

## Rollback Notes

- **Steps 1–2 (`PR_QUERY` expansion):** widening the GraphQL selection is additive and read-only; revert by restoring the prior `reviewThreads(first:100){ nodes { isResolved } }` selection and removing the top-level `comments` block. No state mutation, no migration.
- **Step 31 (envelope field):** `commentTargets` is an additive envelope field; downstream consumers ignore unknown fields, so reverting it is safe and independent.
- **Steps 32–34 (batch dispatch):** if `doRespondComment` misbehaves in production, remove `"respond_comment"` from `RESOLVE_ACTIONS` (step 32) — the resolver still emits the action but the batch falls back to skipping it, restoring pre-feature behavior without touching the resolver.
- **Step 20 (`qrspi_comment_reply.py`):** the only destructive surface is the gh PR comment write. It is append-only (creates replies, never deletes/edits); a stray reply is reversible by deleting the comment on GitHub. No DB, no migration. If the Slice 2 verification gate (step 29) shows a 403, do NOT proceed to Slice 3.
