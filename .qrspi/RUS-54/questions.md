# Questions — Batch addresses reviewer comments on in-review PRs, not just change requests

**Ticket:** RUS-54
**Generated:** 2026-06-08T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does `scripts/qrspi_pr_state.py` currently gather PR review state via the gh GraphQL query, and which fields (review decision, review threads, comments, authors) are already fetched versus absent?
  **Target:** scripts/qrspi_pr_state.py
- Q2: What is the shape of the state envelope that `scripts/qrspi_resolve.py` returns to the orchestrator, and where in that envelope would per-comment data (id, author, body, thread association, in_reply_to_id) need to flow to reach the action decision?
  **Target:** scripts/qrspi_resolve.py
- Q3: How does the batch workflow consume the resolved action and pass per-ticket context into the spawned phase agent prompt, so a new "respond to comment" action could carry comment ids and thread targets?
  **Target:** .claude/workflows/qrspi-batch.js

## API Surface

- Q4: What inputs and outputs does the tested resolver `scripts/qrspi_resolve_state.py` expose, and how does it currently classify a PR with unresolved threads but no CHANGES_REQUESTED as `wait`?
  **Target:** scripts/qrspi_resolve_state.py
- Q5: Which gh REST/GraphQL calls and comment-write paths are already invoked anywhere in the codebase (top-level conversation comment vs. inline review-thread reply via `POST /repos/{owner}/{repo}/pulls/{n}/comments/{comment_id}/replies`), and where would a reply-write helper be wired in?
  **Target:** the module responsible for PR writes (scripts/ and .claude/workflows/qrspi-batch.js)
- Q6: How are reviewer identities and the bot identity (`russelltshermanbot`) currently determined in the codebase — is there existing author/`@me` resolution that distinguishes reviewer-authored from bot-authored comments?
  **Target:** scripts/qrspi_resolve.py and .qrspi/config.json handling

## State Management

- Q7: How is comment/thread idempotency state represented today, if at all — is there any persisted record of which comment ids the agent has already replied to, and where would such a marker live relative to `.qrspi/<id>/` artifacts?
  **Target:** scripts/qrspi_persist.py and .qrspi/<id>/ artifact layout
- Q8: How does the resolver currently order competing actions (advance, submit, land, reset, revise, wait) for a single ticket, and where would a comment-response action be prioritized among them?
  **Target:** scripts/qrspi_resolve_state.py

## Edge Cases

- Q9: How does the current thread-gathering logic distinguish a reviewer-authored comment from a bot-authored reply, and does the existing JSON parsing risk capturing the nested `user.id` instead of the comment `.id` field?
  **Target:** scripts/qrspi_pr_state.py
- Q10: What happens in the resolver when a PR is simultaneously APPROVED and carries an unaddressed reviewer comment — does any existing branch treat APPROVED as terminal in a way that would suppress a comment-response action?
  **Target:** scripts/qrspi_resolve_state.py
- Q11: How does the existing revise path (`scripts/qrspi_revise_amend.py`) terminate and avoid re-triggering on subsequent runs, and what distinguishes that termination signal from a comment-reply that must NOT resolve or close the thread?
  **Target:** scripts/qrspi_revise_amend.py
- Q12: How does the batch loop behave when a single PR has multiple unaddressed reviewer comments across different inline threads and the top level — does the current per-ticket single-action model accommodate multiple targeted replies in one run?
  **Target:** .claude/workflows/qrspi-batch.js

## Testing

- Q13: What patterns do the existing stdlib-only `_test.py` siblings use to assert resolver classifications (e.g., `scripts/qrspi_resolve_state_test.py`, `scripts/qrspi_pr_state_test.py`), and how are PR GraphQL/REST responses faked in those tests?
  **Target:** scripts/qrspi_resolve_state_test.py and scripts/qrspi_pr_state_test.py
- Q14: How is comment-author attribution and idempotency currently exercised in tests, if at all, and what fixtures exist for review threads and comment payloads?
  **Target:** scripts/qrspi_pr_state_test.py

## Observability

- Q15: How does the batch workflow currently surface its per-ticket action decisions and skips (e.g., logging that a PR resolved to `wait`), so a new comment-response action and any decline-with-rationale outcome would be visible in run output?
  **Target:** .claude/workflows/qrspi-batch.js
