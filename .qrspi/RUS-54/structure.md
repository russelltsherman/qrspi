# Structure Outline — Batch addresses reviewer comments on in-review PRs, not just change requests

**Design basis:** design.md @ 2026-06-08T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## New Types

- `CommentTarget { commentId: int (databaseId), author: str (login), body: str, threadType: "inline"|"toplevel", threadId: str|None, lastReplyAuthor: str|None }` — one unaddressed reviewer-authored comment, surfaced per phase by the gather (ref: design.md §Delta `qrspi_pr_state.py`).
- `ReplyEnvelope { ok: bool, replyId: int|None, inReplyToId: int|None, error: str|None }` — JSON stdout contract of the new `qrspi_comment_reply.py` script (ref: design.md §Delta).

## Modified Types

- `PhaseState` (the `phases.<name>` dict inside the gathered state) — add field `commentTargets: list[CommentTarget]` alongside the existing `unresolvedThreads`/`reviewDecision`/`number` (ref: design.md §Delta `qrspi_pr_state.py`, AC1).
- `Decision` (resolver output) — add action value `"respond_comment"` to the action vocabulary; when fired it also carries `phase` and a `commentTargets` payload (ref: design.md §Delta `qrspi_resolve_state.py`, AC1).
- `Envelope` (from `build_envelope()` in `qrspi_resolve.py`) — add top-level field `commentTargets` (per-phase comment-target list), since `decision` keys are fixed and the raw state is dropped today (ref: design.md §Delta `qrspi_resolve.py`, Q2).
- `PR_QUERY` GraphQL (in `qrspi_pr_state.py`) — expand `reviewThreads` nodes to `{ id isResolved comments(first:N){ nodes { databaseId body author{login} } } }` and add a top-level `comments(first:N){ nodes { databaseId body author{login} } }` (ref: design.md §Delta, AC6).

## Contracts

- `unaddressed_reviewer_comments(pr_node: dict, bot_login: str) -> list[CommentTarget]` — pure function in `qrspi_pr_state.py`; given a parsed PR node and the bot/authenticated login, returns reviewer-authored comments with no later bot reply in-thread (inline: bot reply in the same thread's comment chain; top-level: a later bot top-level comment by timestamp/order). Filters out comments where `author.login == bot_login`. Reads ids from `.databaseId` / `.id` API fields, never a JSON-blob regex (ref: AC5, AC6, Decision 1, Decision 2).
- `resolve(state) -> Decision` (modified) — insert a `respond_comment` branch strictly AFTER the reset/revise check and AHEAD of the `wait`/APPROVED sinks: if a phase carries ≥1 `commentTargets`, return `respond_comment` for that phase. Fires even when APPROVED; CR still outranks it (ref: AC1, Decision precedence, Risk Register row 4).
- `qrspi_comment_reply.py` CLI — `--ticket --pr --comment-id --reply-mode {inline|toplevel} --body-file`; inline → `POST /repos/{owner}/{repo}/pulls/{n}/comments/{comment_id}/replies`; top-level → `gh pr comment`; prints `ReplyEnvelope` JSON, capturing the new reply `.id` (ref: AC7, Decision 3).
- `doRespondComment(t, r)` (JS, in `qrspi-batch.js`) — iterates `r.commentTargets` (comment-keyed multiplicity), builds a peer-reviewer worker prompt per comment, invokes the reply script, optionally amends on applied changes, returns `{ticketId, action, summary, prUrl}` (ref: AC2–AC4, Q3, Q12, Q15).

## Slice 1: Comment gather + resolver detection (pure Python core)

**Goal:** `qrspi_pr_state.py` fetches per-comment data and emits `commentTargets` per phase; `qrspi_resolve_state.py` returns the new `respond_comment` action at the correct precedence. End-to-end testable purely through stdlib unit tests with literal GraphQL-node and state fixtures — no gh/git/subprocess needed.
**Files touched:**

- ⚠️ `scripts/qrspi_pr_state.py` — expand `PR_QUERY` (reviewThread + top-level `comments` with `databaseId`/`body`/`author{login}`); add pure `unaddressed_reviewer_comments(pr_node, bot_login)`; carry `commentTargets` into `phases.<name>`.
- ⚠️ `scripts/qrspi_resolve_state.py` — add `respond_comment` to the action vocabulary; insert the detection branch after reset/revise, before `wait`/APPROVED.
- ✨ `scripts/qrspi_pr_state_test.py` additions (or new fixtures within it) — comment-payload fixtures; author-attribution; `databaseId`-not-`user.id` assertion; "bot reply present → comment not unaddressed"; top-level addressed-by-later-bot-comment rule.
- ⚠️ `scripts/qrspi_resolve_state_test.py` — `respond_comment` precedence: CR outranks it; it outranks `wait`; fires when APPROVED; no fire when only bot replies remain.

**Verification:**
- [ ] `python3 scripts/qrspi_pr_state_test.py` passes, including new author-attribution and idempotency fixtures.
- [ ] `python3 scripts/qrspi_resolve_state_test.py` passes, including the four precedence cases.
**Context cost:** M
**Depends on:** none

## Slice 2: Comment-reply write helper + gh-write re-verification gate

**Goal:** A self-locating `qrspi_comment_reply.py` performs the inline and top-level gh REST writes and returns a `ReplyEnvelope`, with its pure core (arg parse, mode→endpoint mapping, response→envelope) unit-tested. Includes the design-mandated end-to-end re-verification that gh PR comment writes succeed in THIS runtime (the gate the ticket cites) before the orchestration relies on it.
**Files touched:**

- ✨ `scripts/qrspi_comment_reply.py` — pure-core/impure-shell; `--ticket --pr --comment-id --reply-mode --body-file`; inline replies endpoint vs `gh pr comment`; self-locating repo root; JSON `ReplyEnvelope` stdout.
- ✨ `scripts/qrspi_comment_reply_test.py` — pure-core unit tests (mode→endpoint, response parse → `replyId`/`inReplyToId`, error envelope).

**Verification:**
- [ ] `python3 scripts/qrspi_comment_reply_test.py` passes.
- [ ] Manual end-to-end: post an inline reply and a top-level comment against a real test PR with the bot credential; confirm both succeed (no 403) and the printed `replyId` matches the created comment. If this fails, the feature is blocked and the `wait` sink stays correct (Risk Register row 1).
**Context cost:** M
**Depends on:** none

## Slice 3: Envelope wiring, batch dispatch, and peer-reviewer worker

**Goal:** Wire the pure detection (Slice 1) and the write helper (Slice 2) into the live orchestration: the resolver envelope carries `commentTargets`, the batch dispatches `respond_comment` to a `doRespondComment` handler iterating comment targets, and the extended revise worker engages each comment as a peer reviewer (answer / apply+amend / decline-with-rationale). Stale "gh PR writes 403" docs corrected. Verifiable end-to-end through one batch pass on a PR carrying a reviewer comment.
**Files touched:**

- ⚠️ `scripts/qrspi_resolve.py` — pass the authenticated login (reuse `_gh_authenticated_login()`) into the gather; re-emit per-phase `commentTargets` in the envelope.
- ⚠️ `.claude/workflows/qrspi-batch.js` — add `respond_comment` to `RESOLVE_ACTIONS`; add a dispatch `case`; add `doRespondComment(t, r)` iterating `r.commentTargets`, invoking `qrspi_comment_reply.py`, amending on applied changes, logging `{ticketId, action, summary, prUrl}`.
- ⚠️ `.claude/agents/qrspi-*` (the existing revise worker definition) — extend so it answers/applies/declines per AC2–AC4, honesty-bound, reusing the self-locating amend mechanism; rationale lands in the in-thread reply (RQ5).
- ⚠️ `.claude/CLAUDE.md` — correct the stale "gh PR writes 403" / `wait`-for-threads assertions.
- ⚠️ `.claude/workflows/qrspi-batch.js` (doc/comment strings) — correct stale 403 assertions (same file as above; covered by that edit).
- ⚠️ `.claude/skills/qrspi-*/SKILL.md` (the batch/revise skill wrapper) — correct the stale 403 assertion.

**Verification:**
- [ ] `node --check .claude/workflows/qrspi-batch.js` passes; `doRespondComment` is reachable via the dispatch switch and `RESOLVE_ACTIONS` includes `respond_comment`.
- [ ] Manual end-to-end batch run against a PR with one unaddressed reviewer comment: the worker posts an in-thread reply; a second batch run does NOT re-respond (idempotency via the observed bot reply); a CR on the same PR still outranks `respond_comment`.
- [ ] `grep` confirms no remaining "gh PR writes 403" / "every gh mutation 403s" assertion in the three touched doc surfaces.
**Context cost:** L
**Depends on:** Slice 1, Slice 2

---

## Unverified Assumptions

- **gh PR comment writes succeed in THIS runtime.** The design treats the 2026-06-08 "403 RESOLVED (classic PAT)" note as fact (RQ1) and proceeds, but every prior in-repo assertion says writes 403. Slice 2's manual end-to-end gate must confirm this before Slice 3 relies on it; if it 403s, the feature is blocked (Risk Register row 1).
- **Bot identity == authenticated identity.** Author-filtering uses `_gh_authenticated_login()` as the bot login (Decision 2 Option A). True today per the design, but an explicit assumption — if the batch ever runs under a credential distinct from the comment-authoring bot, the filter mis-classifies.
- **`first:N` page size for comments is sufficient.** The design writes `comments(first:N)` without pinning N; a thread or conversation with more comments than the cap could hide the latest bot reply and cause a re-fire. The concrete N (and whether pagination is needed) is unspecified and must be chosen in Plan.
- **Top-level "addressed" ordering is reliable.** The deterministic rule is "a later bot top-level comment after the reviewer's comment by timestamp/order" (RQ2). Whether the GraphQL response provides a stable ordering field (e.g. `createdAt`) for top-level comments — versus relying on node array order — is not specified in the design and must be confirmed in Plan.
- **Which agent file is "the existing revise worker."** The Delta says `.claude/agents/qrspi-*` (extend revise) but does not name the exact file. The concrete path is unverified here (no codebase read permitted) and must be identified in Plan/WorkTree before editing.
- **Exact SKILL.md path carrying the stale 403 assertion.** The Docs delta names "SKILL.md" generically; the specific skill wrapper file is unverified and must be located in Plan.
