# Implementation Log — RUS-54: Respond to unaddressed PR review comments

## Session 1 — Slice 1: Comment gather + resolver detection (pure Python core)

**Timestamp:** 2026-06-09T00:00:00Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13, T14, T15, T16, T17, T18, T19
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_pr_state_test.py` → 64 passed, 0 failed (exit 0)
- `python3 scripts/qrspi_resolve_state_test.py` → 33 passed, 0 failed (exit 0)

**Deviations from structure.md:**

- none. `unaddressed_reviewer_comments(pr_node, bot_login)` returns CommentTarget dicts with the exact fields `{commentId, author, body, threadType, threadId, lastReplyAuthor}`; ids read from `.databaseId`/`.id`, authors from `author.login` (no regex). `respond_comment` inserted strictly after reset/revise, ahead of wait/APPROVED sinks; fires when APPROVED, CR outranks.

**Deviations from plan.md:**

- none functionally. Implementation notes (additive, within slice scope):
  - Added a small `ACTIONS` tuple to `qrspi_resolve_state.py` as the explicit "action vocabulary" the plan/structure reference (the resolver previously had only inline string literals). `respond_comment` is a member.
  - `parse_pr_nodes` gained an optional `bot_login=None` param; `commentTargets` defaults to `[]` when no bot login is supplied (matches plan §1.6 default). Existing `parse_pr_nodes` equality-assert tests were updated to include the additive `"commentTargets": []` key, since they do strict dict comparison.
  - Added subprocess helper `_bot_login()` (gh api user -q .login, degrades to "" on error) and threaded `bot_login` through `build_state` -> `phase_pr` and the slice loop, so each `phases.<name>` (and each slice) carries `commentTargets`.
  - `resolve()` decision dict gained an additive `commentTargets` key (defaults `[]`); the `respond_comment` branch carries the phase's aggregated targets. For implementation, `phase_comment_targets` aggregates across slice PRs (mirrors `phase_changes_requested`).

**Notes for next session:**

- The gather now emits `commentTargets: list[CommentTarget]` per phase (and per slice) in the state JSON, and the resolver emits `{action: "respond_comment", phase, commentTargets}`. A downstream slice that consumes `respond_comment` should read the targets off the resolver decision payload (key `commentTargets`).
- New script contract added: `unaddressed_reviewer_comments(pr_node, bot_login) -> list[CommentTarget]` in `scripts/qrspi_pr_state.py` (pure, unit-tested).
- `qrspi_comment_reply.py` (the ReplyEnvelope-emitting script referenced in structure §New Types) is NOT part of Slice 1 — not created here.
- Inline "addressed" = a later bot-authored comment in the same thread (createdAt-ordered). Top-level "addressed" = some bot top-level comment with strictly greater createdAt. Ordering is by `createdAt` ascending, not array order (plan Plan-phase decision).
- `_bot_login()` uses `gh api user`; in tests the bot login is passed explicitly, so no gh dependency in the unit tests.

---
