# PR: RUS-54 Batch responds to unaddressed PR review comments

**Ticket:** RUS-54
**Design:** design.md @ 2026-06-08T00:00:00Z
**Structure:** structure.md @ 2026-06-09T00:00:00Z

## Summary

The PR-gated batch previously swallowed reviewer **comments** that were not formal
change requests: a top-level comment, or a comment on a resolved thread, fell straight
through the resolver to `advance`/`land` (or was masked by the `wait`/APPROVED sinks),
so the reviewer was never answered. This change adds a new `respond_comment` action.
The gather (`qrspi_pr_state.py`) now fetches per-comment data (`databaseId`, `body`,
`author.login`) on both inline review threads and top-level conversation, and a pure
`unaddressed_reviewer_comments()` returns reviewer-authored comments that have no later
bot reply in-thread. The resolver slots `respond_comment` strictly **after** the
reset/revise check and **ahead of** the `wait`/APPROVED sinks (it fires even when
APPROVED; a formal CR still outranks it), a new self-locating `qrspi_comment_reply.py`
posts the in-thread reply, and the batch's `doRespondComment` spawns a peer-reviewer
worker per comment that answers / applies+amends / declines-with-rationale.
**Reviewer focus:** (1) resolver precedence in `qrspi_resolve_state.py` — CR must
outrank `respond_comment`, which must outrank `wait`; (2) author-attribution /
anti-loop correctness in `unaddressed_reviewer_comments` (reads `.databaseId`, not the
nested `user.id`; idempotency is structural via the observed bot reply, no ledger);
(3) the **deferred manual gh-write gate** — no live-PR write was executed in CI (see
Testing Summary and Risks).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: gather fetches per-comment data; resolver emits `respond_comment` after reset/revise, before `wait`, even when APPROVED | `qrspi_pr_state.py:unaddressed_reviewer_comments`, `qrspi_resolve_state.py:resolve` (respond_comment branch) | `qrspi_resolve_state_test.py` (precedence cases), `qrspi_pr_state_test.py` |
| AC2: worker answers questions faithfully from real state (honesty-bound) | `qrspi-batch.js:doRespondComment` (inline peer-reviewer `agent()` prompt) | manual e2e (deferred — T38 live portion) |
| AC3: apply (amend phase commit) or decline, rationale in thread reply | `qrspi-batch.js:doRespondComment` (via `qrspi_revise_amend.py` + `qrspi_comment_reply.py`) | manual e2e (deferred — T38 live portion) |
| AC4: decline + explain when change is incorrect/unsafe (peer, not order-taker) | `qrspi-batch.js:doRespondComment` (worker prompt directive) | manual e2e (deferred — T38 live portion) |
| AC5: responded comment does not retrigger; own bot comments never treated as input | `qrspi_pr_state.py:unaddressed_reviewer_comments` (author filter + in-thread bot-reply marker) | `qrspi_pr_state_test.py` (bot reply present → not unaddressed; bot-only → no fire) |
| AC6: attribute by `.databaseId`/`author.login` field, not a regex over the blob (avoids nested `user.id`) | `qrspi_pr_state.py:unaddressed_reviewer_comments` | `qrspi_pr_state_test.py` (`databaseId`-not-`user.id` assertion) |
| AC7: reply lands in reviewer's own thread (inline `.../comments/{id}/replies`; top-level `gh pr comment`); never via commit/PR body | `qrspi_comment_reply.py:mode_to_request`, `response_to_envelope` | `qrspi_comment_reply_test.py` (mode→endpoint, response→envelope) |

## Changes by Slice

### Slice 1: Comment gather + resolver detection (pure Python core)

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_pr_state.py` | ⚠️ modified (expand `PR_QUERY`; add `unaddressed_reviewer_comments`; carry `commentTargets` per phase) | +111, -6 |
| `scripts/qrspi_resolve_state.py` | ⚠️ modified (add `respond_comment` to action vocab + detection branch) | +44, -0 |
| `scripts/qrspi_pr_state_test.py` | ⚠️ modified (comment-payload fixtures, author-attribution, idempotency) | +101, -7 |
| `scripts/qrspi_resolve_state_test.py` | ⚠️ modified (precedence cases) | +69, -4 |

### Slice 2: Comment-reply write helper + gh-write re-verification gate

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_comment_reply.py` | ✨ new (`--ticket --pr --comment-id --reply-mode --body-file`; `ReplyEnvelope` stdout) | +251 |
| `scripts/qrspi_comment_reply_test.py` | ✨ new (pure-core unit tests) | +124 |

### Slice 3: Envelope wiring, batch dispatch, and peer-reviewer worker

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_resolve.py` | ⚠️ modified (re-emit top-level `commentTargets` via `comment_targets_of`) | +23, -0 |
| `scripts/qrspi_resolve_test.py` | ✨ new (top-level `commentTargets` + `comment_targets_of` cases) | +21 |
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified (`RESOLVE_ACTIONS` + dispatch case + `doRespondComment`; corrected 403 strings) | +130, -15 |
| `.claude/CLAUDE.md` | ⚠️ modified (corrected stale "gh PR writes 403" / `wait`-for-threads docs; added respond_comment lifecycle) | +12, -6 |
| `.claude/skills/qrspi-work/SKILL.md` | ⚠️ modified (added `respond_comment` action section + dispatch-table row; corrected 403 assertion) | +72, -23 |

### Phase artifacts (non-code)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-54/questions.md` | ✨ new | +53 |
| `.qrspi/RUS-54/research.md` | ✨ new | +433 |
| `.qrspi/RUS-54/design.md` | ✨ new | +131 |
| `.qrspi/RUS-54/structure.md` | ✨ new | +84 |
| `.qrspi/RUS-54/plan.md` | ✨ new | +154 |
| `.qrspi/RUS-54/worktree.md` | ✨ new | +78 |
| `.qrspi/RUS-54/impl-log.md` | ✨ new | +90 |

## Testing Summary

- [x] Slice 1: gather unit tests — `python3 scripts/qrspi_pr_state_test.py` — 64 passed, 0 failed
- [x] Slice 1: resolver unit tests — `python3 scripts/qrspi_resolve_state_test.py` — 33 passed, 0 failed
- [x] Slice 2: reply-helper unit tests — `python3 scripts/qrspi_comment_reply_test.py` — 15 passed, 0 failed
- [x] Slice 3: envelope unit tests — `python3 scripts/qrspi_resolve_test.py` — 59 passed, 0 failed
- [x] Slice 3: batch syntax — `node --check .claude/workflows/qrspi-batch.js` — passes
- [x] Slice 3: stale-403 doc sweep — `grep -rn "gh PR writes 403|every gh mutation 403s|gh.*403" .claude/CLAUDE.md .claude/workflows/qrspi-batch.js .claude/skills/` — no matches (exit 1)
- [ ] **DEFERRED — manual gh-write gate (Slice 2 T29 + Slice 3 T38 live portion):** post a real inline + top-level reply against a live test PR with the bot credential; confirm no 403, `replyId` matches the created comment, and a second batch pass does NOT re-respond. Not executed in CI — it requires a live PR and network writes; it is the reviewer/orchestrator's manual checkpoint. Per project memory (`gh-pr-writes-impossible-crossaccount-pat.md`, 2026-06-08) gh comment writes are expected to succeed (classic PAT), but this was not asserted by running it.

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| Peer-reviewer worker location | Structure §Slice 3 / RQ4: "extend the existing revise worker (`.claude/agents/qrspi-*`)" | Implemented as an inline `agent()` prompt inside the new `doRespondComment()` in `qrspi-batch.js` | No `.claude/agents/*` revise-worker FILE exists — the revise worker is itself an inline `agent()` prompt in `doRevise()`. The structure's file reference predated the Slice 1 codebase read; the inline `doRespondComment` worker is the faithful equivalent. |
| `qrspi_comment_reply.py` owner/repo args | Structure Contract names `--ticket --pr --comment-id --reply-mode --body-file` (owner/repo implied resolved) | Script takes neither owner nor repo on the CLI; derives both via `resolve_owner_repo()` (`gh repo view`) | Matches the self-locating convention of `qrspi_revise_amend.py`/`qrspi_persist.py`; the plan said "resolve owner/repo (self-located)". |
| `build_state` `bot_login` param (T30) | Plan T30: "pass `_gh_authenticated_login()` into the gather" | No new param added | `build_state` already self-resolves the bot login via its own `_bot_login()` and threads it through; `qrspi_resolve.py` calls `build_state` (not `parse_pr_nodes` directly), so the login was already wired. Adding a param would be dead surface. |
| Top-level reply `replyId` capture | AC7 "captures the created `.id`" | Inline replies capture `.id` (fail-closed on missing/null); top-level returns `ok=true, replyId=null` | `gh pr comment` prints a URL, not JSON — there is no numeric id to capture for top-level. Faithful reading of the constraint. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| gh PR comment writes still 403 in this environment despite MEMORY's "RESOLVED" note | **accepted / unverified** — the live write gate was NOT run (deferred). If it 403s, the worker returns `ok:false` and `respond_comment` must not be relied on; the `wait` sink stays correct. | Revert Slice 3 (`qrspi-batch.js` dispatch + `doRespondComment`); the resolver still emits `respond_comment` but nothing acts on it, or revert Slices 1–3 wholesale. |
| Reply loop: bot replies to its own reply / re-replies each run (AC5/AC6) | **mitigated** — author-filter by resolved bot login + re-derive "unaddressed" from the in-thread bot reply (structural idempotency, no ledger); covered by "bot reply present → no re-fire" and `databaseId`-not-`user.id` tests. | n/a (covered by tests); to disable, revert Slice 1. |
| Top-level "already addressed" is heuristic (no thread structure) | **mitigated / accepted-coarser** — deterministic rule: a later bot top-level comment by `createdAt` order marks it addressed; covered by fixtures. Top-level idempotency is coarser than inline by design. | Revert Slice 1's top-level `comments` query expansion. |
| `respond_comment` mis-prioritized (masks a CR, or fires on APPROVED that should advance) | **mitigated** — slotted strictly after reset/revise, before `wait`/APPROVED; precedence pinned by resolver tests (CR outranks; outranks `wait`; fires when APPROVED). | Remove the `respond_comment` branch from `qrspi_resolve_state.py`. |
| Multiple comments across threads exceed the one-action-per-ticket model | **mitigated** — `doRespondComment` iterates `r.commentTargets` (comment-keyed multiplicity); each reply is independent + idempotent, so a partial run self-heals next pass. | n/a. |
| Worker over-complies (applies an unsound/unsafe change) violating AC4 | **mitigated (design-level)** — peer-reviewer prompt enforces honesty/decline-with-rationale; applied changes go through the existing amend+verify gate, never a blind write. **Not** asserted by an automated test (worker behavior is LLM-driven). | n/a; tighten the worker prompt if observed. |

## Open Items

- **DEFERRED MANUAL GATE (carried from Slice 2 T29 + Slice 3 T38 live portion):** no live-PR end-to-end run was executed — post a real inline + top-level reply with the bot credential, confirm no 403, `replyId` matches, and the second pass does not re-respond. This is the design-mandated Risk-Register-row-1 verification and must be run by the reviewer/orchestrator before relying on `respond_comment` in production.
- **Worker behavior (AC2–AC4) has no automated coverage** — answer/apply/decline correctness is LLM-driven and verified only by the deferred manual e2e. The CR-outranks-`respond_comment` portion of T38 *is* covered by passing resolver unit tests.
- **`first:N` comment page size** — `PR_QUERY` caps comments per thread/conversation; a thread with more comments than the cap could hide the latest bot reply and cause a re-fire. Pagination is not implemented; the chosen N is assumed sufficient.
- **Bot identity == authenticated identity** is an explicit assumption — if the batch ever runs under a credential distinct from the comment-authoring bot, the author filter mis-classifies.
