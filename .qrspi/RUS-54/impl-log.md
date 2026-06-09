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

## Session 2 — Slice 2: Comment-reply write helper + gh-write re-verification gate

**Timestamp:** 2026-06-09T00:00:00Z
**Tasks completed:** T20, T21, T22, T23, T24, T25, T26, T27, T28
**Tasks failed:** none (T29 manual gh-write gate deferred — see notes)
**Tests:**

- `python3 scripts/qrspi_comment_reply_test.py` → 15 passed, 0 failed (exit 0)

**Deviations from structure.md:**

- none. `qrspi_comment_reply.py` implements `--ticket --pr --comment-id --reply-mode {inline|toplevel} --body-file`; inline → `POST /repos/{owner}/{repo}/pulls/{n}/comments/{comment_id}/replies`; top-level → `gh pr comment`; stdout is the `ReplyEnvelope {ok, replyId, inReplyToId, error}` JSON. `mode_to_request` and `response_to_envelope` are the pure core, exactly as the plan names them.

**Deviations from plan.md:**

- none functionally. Implementation notes (additive, within slice scope):
  - Owner/repo are resolved via `resolve_owner_repo()` (`gh repo view --json owner,name`), self-located like the rest of the harness, since the plan says "resolve owner/repo (self-located)" but the existing `qrspi_pr_state.py` takes owner/repo as explicit CLI args. This script takes neither owner nor repo on the CLI — it derives both — matching the self-locating convention of `qrspi_revise_amend.py`/`qrspi_persist.py`.
  - `response_to_envelope` fails CLOSED for inline replies on non-JSON / missing / null `.id` (ok=false + error) rather than reporting success with a null replyId. Top-level returns ok=true with replyId=null because `gh pr comment` prints a URL, not JSON (no numeric id to capture). This is the faithful reading of "captures the created `.id`" + the AC7 replyId-match check.
  - Added a small pure `error_envelope()` helper plus `_as_int_or_none`/`_envelope` so the impure `main()` failure paths (body-file read error, owner/repo resolve error, gh subprocess non-zero) all emit the canonical `ok:false` ReplyEnvelope. `error_envelope` is unit-tested too.

**Notes for next session:**

- `scripts/qrspi_comment_reply.py` exists with pure core `mode_to_request(reply_mode, owner, repo, pr, comment_id, body) -> dict` and `response_to_envelope(reply_mode, raw_response, in_reply_to_id) -> ReplyEnvelope`. Downstream orchestration (Slice 3) invokes the CLI once per `CommentTarget`, passing `--reply-mode` = the target's `threadType` and `--comment-id` = the target's `commentId`, with the reply body written to a `--body-file`.
- The CLI prints the `ReplyEnvelope` JSON to stdout and exits 0 only when `ok:true`; non-zero exit + `ok:false` envelope on any failure. Slice 3 should read `ok`/`replyId` off stdout, not infer success from exit code alone.
- T29's manual gh-write re-verification gate (post a real inline + top-level reply against a live test PR with the bot credential, confirm no 403 and replyId matches) was NOT executed here — it needs a live PR and network writes, which is the reviewer/orchestrator's manual checkpoint, not an automated unit test. Per project memory (`gh-pr-writes-impossible-crossaccount-pat.md`, 2026-06-08) gh PR writes now succeed with the bot's classic PAT, so the gate is expected to pass, but this was not asserted by running it. If that gate ever 403s, Slice 3 must NOT rely on `respond_comment` and the `wait` sink stays correct (Risk Register row 1).

---
