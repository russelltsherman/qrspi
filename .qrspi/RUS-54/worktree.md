# Work Tree — Batch addresses reviewer comments on in-review PRs, not just change requests

**Plan basis:** plan.md @ 2026-06-09T00:00:00Z
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T3 → T4 → T5 → T6 → T7 → T8 → T19 → T20 → T22 → T23 → T24 → T28 → T29 → T30 → T31 → T32 → T33 → T34 → T35 → T38

## Session 1 — Slice 1: Comment gather + resolver detection (pure Python core)

**Load:** structure.md §Contracts (CommentTarget), structure.md §Types, plan.md §Slice 1, plan.md §Plan-phase decisions
**Estimated context:** ~22% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Expand `reviewThreads` selection in `PR_QUERY` (qrspi_pr_state.py) to fetch per-comment data (id, databaseId, body, createdAt, author.login) | — | §1.1 | S | pending |
| T2 | Add top-level `comments(first:100)` selection to `PR_QUERY` PR node | T1 | §1.2 | S | pending |
| T3 | Add pure `unaddressed_reviewer_comments(pr_node, bot_login) -> list[CommentTarget]` in qrspi_pr_state.py; read `.databaseId`/`author.login`, filter bot author | T2 | §1.3 | M | pending |
| T4 | Implement inline rule in `unaddressed_reviewer_comments` (no later bot reply in thread; threadType="inline") | T3 | §1.4 | M | pending |
| T5 | Implement top-level rule (no bot top-level comment with greater createdAt; order by createdAt asc; threadType="toplevel") | T4 | §1.5 | M | pending |
| T6 | Carry `commentTargets` into each `phases.<name>` via parse path / `parse_pr_nodes()`, accepting bot login | T5 | §1.6 | M | pending |
| T7 | Add `"respond_comment"` to action vocabulary in qrspi_resolve_state.py | T6 | §1.7 | S | pending |
| T8 | Insert `respond_comment` branch in `resolve(state)` — after reset/revise, ahead of wait/APPROVED sinks; fires when APPROVED, CR outranks | T7 | §1.8 | M | pending |
| T9 | Test (qrspi_pr_state_test.py): inline reviewer comment, no bot reply → one CommentTarget; assert databaseId/author.login/inline | T4 | §1.9 | S | pending |
| T10 | Test: bot reply later in same inline thread → not returned (idempotency/AC5) | T4 | §1.10 | S | pending |
| T11 | Test: top-level reviewer comment with later bot top-level → not returned; without → returned (toplevel) | T5 | §1.11 | S | pending |
| T12 | Test: comment authored by bot_login always filtered out | T3 | §1.12 | S | pending |
| T13 | Test (qrspi_resolve_state_test.py): commentTargets + CHANGES_REQUESTED → reset/revise, not respond_comment | T8 | §1.13 | S | pending |
| T14 | Test: commentTargets + unresolved threads / not-APPROVED → respond_comment (outranks wait) | T8 | §1.14 | S | pending |
| T15 | Test: commentTargets + APPROVED → respond_comment (fires when APPROVED) | T8 | §1.15 | S | pending |
| T16 | Test: all-bot-reply comments (empty commentTargets) → no respond_comment | T8 | §1.16 | S | pending |
| T17 | Run `python3 scripts/qrspi_pr_state_test.py` — all pass | T9, T10, T11, T12 | §1.17 | S | pending |
| T18 | Run `python3 scripts/qrspi_resolve_state_test.py` — all pass | T13, T14, T15, T16 | §1.18 | S | pending |
| T19 | **Verify Slice 1** — both suites exit 0; field-reads not regex; respond_comment slotted correctly | T17, T18 | §1.19 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified (pure Python core landed). Fresh context for Slice 2, which depends only on the Slice 1 contract (CommentTarget) plus a new standalone CLI — none of Slice 1's test internals need to stay loaded.

## Session 2 — Slice 2: Comment-reply write helper + gh-write re-verification gate

**Load:** structure.md §Contracts (CommentTarget, ReplyEnvelope), plan.md §Slice 2, impl-log.md §Slice 1 (notes only)
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T20 | Create `scripts/qrspi_comment_reply.py` — self-locating CLI (pure-core/impure-shell) printing a ReplyEnvelope JSON | T19 | §2.20 | M | pending |
| T21 | Add argparse: `--ticket`, `--pr`, `--comment-id`, `--reply-mode {inline\|toplevel}`, `--body-file` | T20 | §2.21 | S | pending |
| T22 | Add pure `mode_to_request(reply_mode, owner, repo, pr, comment_id, body) -> dict` (inline→REST replies POST; toplevel→gh pr comment) | T20 | §2.22 | M | pending |
| T23 | Add pure `response_to_envelope(reply_mode, raw_response, in_reply_to_id) -> ReplyEnvelope` capturing created `.id` | T22 | §2.23 | M | pending |
| T24 | Add impure `main()`: resolve owner/repo, subprocess `gh api`/`gh pr comment`, feed through response_to_envelope, print JSON; failure → ok:false envelope | T21, T23 | §2.24 | M | pending |
| T25 | Create `scripts/qrspi_comment_reply_test.py` — stdlib-only, table-driven, pure-core only | T22, T23 | §2.25 | S | pending |
| T26 | Test `mode_to_request`: inline → replies POST path+body; toplevel → gh pr comment form | T25 | §2.26 | S | pending |
| T27 | Test `response_to_envelope`: success → ok=true, replyId from .id, correct inReplyToId; failure → ok=false, error set, replyId=null | T25 | §2.27 | S | pending |
| T28 | Run `python3 scripts/qrspi_comment_reply_test.py` — all pure-core pass | T26, T27 | §2.28 | S | pending |
| T29 | **Verify Slice 2** — pure suite exits 0; manual gh-write gate: inline + toplevel reply against real test PR both return ok:true (no 403), replyId matches. If either 403s, STOP — Slice 3 blocked, wait sink stays correct | T28 | §2.29 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete and the gh-write re-verification gate passed (the design-mandated hard gate; a 403 here blocks Slice 3 entirely). Fresh context for Slice 3, which wires the verified CLI into the resolver envelope, the batch dispatch, and the worker/docs — a different file surface (qrspi_resolve.py, qrspi-batch.js, agents/skills/docs) than Slice 2's standalone CLI internals.

## Session 3 — Slice 3: Envelope wiring, batch dispatch, and peer-reviewer worker

**Load:** structure.md §Contracts (CommentTarget, ReplyEnvelope), plan.md §Slice 3, impl-log.md §Slice 1–2 (notes only)
**Estimated context:** ~28% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T30 | Modify qrspi_resolve.py — pass authenticated login (`_gh_authenticated_login()`) into gather so comments filter by bot login | T29 | §3.30 | S | pending |
| T31 | Modify qrspi_resolve.py `build_envelope()` — re-emit top-level `commentTargets` field in the envelope | T30 | §3.31 | M | pending |
| T32 | Add `"respond_comment"` to `RESOLVE_ACTIONS` set in qrspi-batch.js | T31 | §3.32 | S | pending |
| T33 | Add `case "respond_comment":` to dispatch switch calling `doRespondComment(t, r)` | T32 | §3.33 | S | pending |
| T34 | Add `doRespondComment(t, r)` — iterate `r.commentTargets`, per-comment build worker prompt, stage reply body, invoke qrspi_comment_reply.py, amend phase commit only on change, return result | T33 | §3.34 | L | pending |
| T35 | Extend revise worker agent def (`grep -rl "CHANGES_REQUESTED\|revise" .claude/agents/`) — engage each comment as peer reviewer per AC2–AC4; rationale lands in in-thread reply (RQ5) | T34 | §3.35 | M | pending |
| T36 | Modify .claude/CLAUDE.md — correct stale "gh PR writes 403"/wait-for-threads assertions to reflect respond_comment + classic-PAT writes | T31 | §3.36 | S | pending |
| T37 | Modify batch/revise SKILL.md (`grep -rl "403" .claude/skills/`) — correct stale 403 assertion | T35 | §3.37 | S | pending |
| T38 | **Verify Slice 3** — `node --check` passes, doRespondComment reachable; manual e2e batch posts in-thread reply, second run no re-respond, CR outranks; grep finds no stale 403 across CLAUDE.md/qrspi-batch.js/skills | T34, T35, T36, T37 | §3.38 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 complete — feature fully wired and verified end-to-end. No further sessions; stack is ready for PR review.
