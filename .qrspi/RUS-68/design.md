# Design — qrspi_cleanup.py falsely reports remote branch deletion that never happened

**Ticket:** RUS-68
**Research basis:** research.md @ 2026-06-11T00:00:00Z
**Questions basis:** questions.md @ 2026-06-11T00:00:00Z (answered — the answered
questions are integrated into this design; every `(ref: Qn)` below cites the corresponding
answered question)
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## Current State

Cleanup discovers a ticket's remote refs by intersecting two sources: the ticket's branch names come from the main checkout's locally-tracked branches via `git branch --list <ticket>/*` in `_stack_branches`, and the refs actually on origin come directly from origin via `git ls-remote --heads origin` in `_prune_remote_refs`; the reported set is `remotes = [b for b in branches if b in present]`, so an origin ref with no matching local branch name is never even considered (ref: Q1). The destroy branch runs three steps in fixed order — remove worktree, delete local branches, then "prune" remote refs — so remote handling runs after both the worktree and the local branches are already gone (ref: Q2).

The `removed.remotes` field is populated from presence, not from any deletion result: `_prune_remote_refs` returns the presence list whether or not anything was actually deleted, never re-checks origin afterward, and never inspects what was pruned (ref: Q3). There is in fact no direct remote-ref deletion at all — no `git push origin --delete`, no delete refspec. The only remote-mutating command is `gt sync --force`, which prunes based on local branch + merged-PR state, and which therefore needs a local branch tracking the merged PR to act — but those local branches were already deleted in step 2 (ref: Q5). Because the branch set is captured once at run start and is purely main-checkout-local, there is no separate ticket-to-remote-branch record anywhere (ref: Q7).

Remote deletion is a single all-at-once `gt sync --force` call with no per-ref tracking and no per-ref outcome capture (ref: Q8). Already-absent origin refs are silently excluded by the `if b in present` filter and treated as a clean no-op (ref: Q9). Error surfacing is asymmetric: a non-zero `gt sync` exit raises and yields `ok:false`, but a zero-exit run that pruned nothing still returns the presence list and reports `ok:true` with those refs listed as deleted (ref: Q10). In the RUS-40 scenario — branches that lived only in a now-removed worktree — `_stack_branches` enumerates an empty set from the main checkout, so the stack is classified `skip` ("not fully merged") and the orphaned refs are neither discovered, deleted, nor reported (ref: Q11).

No test covers any of this: `qrspi_cleanup_test.py` is stdlib-only and exercises only the pure `classify_cleanup` decision, with no temp repo, no fake remote, and no stubbed subprocess, so no test can observe post-run remote state (ref: Q12, Q13). The script emits no logging and only the single JSON envelope on stdout, providing no signal a maintainer or the Reconcile pass could use to detect stranded refs (ref: Q14). The repo-wide convention is a pure-classifier / impure-mechanics split where mechanics are not unit-tested, and every reap mechanic uses pre-deletion presence as its "removed" proxy (ref: Discovered Patterns).

## Desired End State

- **AC1** — After cleanup reports a ref in `removed.remotes`, that ref is genuinely gone from origin. The script deletes each ref directly (not via a side-effect of `gt sync`) and confirms absence before reporting it.
- **AC2** — `removed.remotes` lists only refs the run actually deleted. A ref the run attempted but failed to delete is excluded from `removed.remotes` and surfaced as a failure (envelope `ok:false` or a dedicated failure field), never reported as removed.
- **AC3** — A merged ticket whose branches existed only in a now-removed worktree has its stranded origin refs discovered and deleted. Remote-ref discovery no longer depends solely on locally-tracked branch names; an origin-driven discovery path (matching `<ticket>/*` ref names from `git ls-remote`) covers the worktree-only case.
- **AC4** — A test exercises the deletion path against a real-or-faked origin and asserts `removed.remotes` reflects actual post-run absence. This test fails against today's presence-based reporting.

Constraints preserved: an already-absent origin ref remains a clean no-op success (idempotency); dry-run reports what would be deleted and mutates nothing.

Out of scope (unchanged): the destroy/skip/blocked decision logic, local worktree and local-branch removal, and GitHub repo-level auto-delete settings.

## Delta

- **Modify `scripts/qrspi_cleanup.py`:**
  - Fix the `gt sync --force` remote-prune in `_prune_remote_refs` so it actually mutates origin: the prune must run while the local branch `gt` keys off **still exists** (reorder the `gt`-driven remote prune **before** local-branch deletion, or re-establish the tracking ref `gt` needs), per-ref where `gt` allows. Remote mutation **stays within `gt`** — the harness does NOT introduce `git push origin --delete` (RQ3 / QRSPI git policy) (addresses Q3, Q5, Q8).
  - After the prune, re-query origin with a read-only `git ls-remote` to confirm each ref is absent; only confirmed-absent refs enter `removed.remotes`. Any ref still present lands in `failedRemotes` (addresses AC1, AC2, Q14).
  - Add an origin-driven discovery path: derive candidate `<ticket>/*` refs from the `git ls-remote` snapshot itself, not only from `_stack_branches`, so worktree-only refs are found (addresses AC3, Q1, Q11). This feeds an **additive, alternate stranded-ref reaping path** that leaves `classify_cleanup` untouched — see RQ1 (the documented destroy/skip decision logic is intact).
  - Add a `failedRemotes` list to the envelope so a ref that could not be deleted is visibly distinct from one that was. Partial failure is reported as **`ok:true` with a non-empty `failedRemotes`** (a retriable condition for the batch Reconcile pass), NOT `ok:false` — `ok:false` stays reserved for genuine infrastructure errors (RQ2) (addresses AC2).
- **Modify `scripts/qrspi_cleanup_test.py`:** add a fixture-backed test (temp git repo + local bare "origin") exercising `_prune_remote_refs`/`run` and asserting post-run `git ls-remote` shows the refs gone and `removed.remotes` matches reality. This breaks the existing stdlib-only / pure-classifier-only convention (addresses AC4, Q12, Q13 — flagged as a NEW PATTERN below).
- **Modify `.claude/workflows/qrspi-batch.js` (consumer, light):** the `failedRemotes` field is surfaced in the log line at `:816-817` so stranded refs are visible to the operator, and a non-empty `failedRemotes` schedules the ticket for a **Reconcile retry** rather than a halt (RQ2 — partial failure is retriable, `ok` stays `true`). No envelope-shape break for existing fields.

## Pattern Decisions

### Decision 1: How to actually delete remote refs

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Per-ref `git push origin --delete <ref>`, capture each rc | Direct; deterministic; per-ref outcome is observable; no dependence on local branches existing (fixes Q2/Q5 ordering trap) | **Violates QRSPI git policy — all VC mutation goes through `gt`, never raw `git push` (RQ3); ruled out** |
| B | Keep `gt sync --force` but re-query origin afterward to derive the true deleted set | Minimal change to the delete mechanism | `gt sync` still keys off now-deleted local branches (Q5), so it may delete nothing; re-query only corrects the *report*, not the *action* — fails AC3 |
| **D** | Keep `gt`-mediated remote mutation but ensure the local tracking ref `gt` keys off **still exists** when the prune runs (reorder the `gt` remote prune before local-branch deletion, or re-establish the ref), then re-query origin (read-only `git ls-remote`) to derive the true deleted set; unmatched refs → `failedRemotes` | Stays within `gt` policy (RQ3); fixes the Q2/Q5 ordering trap that made `gt sync` a no-op; per-ref outcome confirmed by post-prune read | Requires careful reordering so `gt` has a ref to act on; the additive stranded-ref path (RQ1) handles the worktree-only case where no local ref exists |

**Recommendation:** Option D
**Rationale:** The root cause is that deletion is delegated to `gt sync`, which keys off local branch state that no longer exists at step 3 (ref: Q2, Q5). Option A (a direct per-ref `git push --delete`) would sever that dependency, but it **violates the QRSPI git policy** that all version-control mutation flows through Graphite (RQ3) — so it is ruled out. Option B corrects only the *report*, leaving the action broken (ref: Q11). Option D keeps remote mutation **within `gt`** while fixing the two real defects: it makes the local tracking ref `gt` needs present at prune time (so the mutation actually happens), and it confirms the outcome with a read-only `git ls-remote` so `removed.remotes` reflects reality and any survivor lands in `failedRemotes` (AC2). The worktree-only case, where no local ref exists for `gt` to key off, is handled by the additive stranded-ref path (RQ1).
**NEW PATTERN?** No — it keeps the existing `gt`-mediated remote-mutation pattern; only the ordering and the presence→confirmed-outcome proxy change.

### Decision 2: Discovering worktree-only refs (AC3)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Derive ticket refs from the `git ls-remote` snapshot by matching `<ticket>/*` directly, union with `_stack_branches` | Origin-driven; catches refs with no local branch (the RUS-40 case); origin is the authority for what to delete | Must reach deletion when local branches are empty — resolved by the additive stranded-ref path that leaves `classify_cleanup` intact (RQ1), not by changing the documented decision logic |
| B | Keep local-branch-only discovery, document the worktree-only case as unsupported | Smallest change | Directly fails AC3 — the named scenario |

**Recommendation:** Option A
**Rationale:** Discovery is currently wholly local-branch-driven, which is exactly why a vanished-worktree ticket strands refs (ref: Q1, Q7, Q11). Matching `<ticket>/*` against the `git ls-remote` snapshot the function already fetches makes origin the discovery authority, with no new dependency.
**NEW PATTERN?** No — it reuses the existing `git ls-remote` snapshot and the `<ticket>/*` naming convention already relied on by `_stack_branches`.

### Decision 3: Testing the deletion path (AC4)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Temp git repo + local bare repo as "origin" fixture; run real deletes; assert via `git ls-remote` | Tests true behavior; observes post-run state; directly satisfies AC4 | Breaks the stdlib-only / pure-classifier-only convention; needs `git` available in test env |
| B | Stub subprocess calls and assert the delete commands were issued | Stays stdlib-only; fast | Asserts intent, not effect — would still pass if the delete silently no-ops; weaker against the exact false-success bug |

**Recommendation:** Option A
**Rationale:** AC4 requires a test that fails against presence-based reporting; only observing real post-run origin state (Option A) distinguishes "reported deleted" from "actually deleted" (ref: Q12, Q13, Q14). A stub (Option B) asserts the command was issued but cannot catch a zero-exit-but-no-op, which is the precise gap (ref: Q10, Inconsistency 5).
**NEW PATTERN?** Yes — the repo convention is "test pure functions only; do not touch git/gh/subprocess" (ref: Q13, Discovered Patterns). A git-fixture test deliberately departs from it because the bug lives entirely in the untested impure mechanics and cannot be caught by pure-function testing. Justification: the defect is unobservable without exercising real git effects.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Origin-driven discovery deletes refs the run shouldn't (e.g. a still-open `<ticket>/*` PR ref) | med | high | Gate deletion on the same destroy classification; only delete when the stack is confirmed fully merged; keep destroy/skip decision logic unchanged (out of scope) |
| Classification still returns `skip` for an empty local-branch set, so the destroy branch never runs and AC3 deletion is never reached | med | high | Resolved by RQ1 — an additive, alternate stranded-ref reaping path (gated on the same fully-merged confirmation) handles the worktree-only case; `classify_cleanup` is left **unchanged**, so the documented decision logic stays intact |
| Git-fixture test is flaky or unavailable in CI/sandbox (no git, or network assumptions) | low | med | Use a local bare repo as origin (no network); skip-guard if `git` absent; keep the pure-classifier tests as-is alongside |
| Envelope shape change (`failedRemotes` semantics) breaks the batch consumer's parser | low | med | Add `failedRemotes` additively; do not rename/remove existing `removed.*`; partial failure is `ok:true` + `failedRemotes` (retriable, RQ2), never `ok:false`; update `parseCleanupEnvelope`/log line + the Reconcile-retry trigger in lockstep (ref: Q4) |
| Per-ref `git push --delete` non-zero on a ref already absent races idempotency | low | low | Treat already-absent as success no-op; confirm via post-delete `git ls-remote` rather than trusting the push rc (ref: Q9) |

## Resolved Questions

These three open questions were resolved by reviewer direction on the design PR; the
resolutions are now binding constraints on the Delta above.

- **RQ1 (was OQ1) — leave the documented decision logic intact.** AC3 requires deleting
  refs for a ticket whose local branch set is empty, but today an empty branch set drives
  classification to `skip` and the destroy branch never runs (ref: Q11). **Resolution:** the
  documented destroy/skip/blocked decision logic (`classify_cleanup`) stays **unchanged** —
  it is not retriggered, reordered, or re-thresholded. Origin-driven discovery feeds an
  **alternate, additive destroy trigger** for the worktree-only case: when `classify_cleanup`
  returns `skip` *because the local branch set is empty* AND `git ls-remote` shows merged
  `<ticket>/*` refs on origin, a separate stranded-ref reaping path runs. It is gated on the
  same fully-merged confirmation the documented logic already requires (a ref is only deleted
  once its PR is confirmed merged), so the documented decision is never overridden — the new
  path only *adds* a route to deletion for refs the existing classifier structurally cannot
  see. The Out-of-Scope line ("changing the destroy/skip decision logic") is preserved
  verbatim: `classify_cleanup` is untouched.

- **RQ2 (was OQ2) — the batch Reconcile pass should retry.** On a partial failure (some refs
  deleted, some not). **Resolution:** the envelope is **`ok:true` with a populated
  `failedRemotes` list**, NOT `ok:false`. Rationale: a stranded ref is a *retriable* condition,
  not an infrastructure hard-stop — emitting `ok:true` + `failedRemotes` lets the batch
  Reconcile pass **retry** the deletion on a subsequent pass (idempotent: a still-present ref
  is rediscovered and re-attempted, an already-deleted one drops out). Reserving `ok:false`
  for genuine infrastructure errors (e.g. `gt`/git unreachable) keeps the HARD-STOP semantics
  honest. The batch consumer therefore: logs `failedRemotes`, and on a non-empty
  `failedRemotes` schedules the ticket for a Reconcile retry rather than halting (ref: Q4 — the
  field is additive; existing `removed.*` fields are unchanged).

- **RQ3 (was OQ3) — stay within `gt` policy for remote mutations.** **Resolution:** remote-ref
  deletion **stays within `gt`** (QRSPI git policy: all version-control mutation goes through
  Graphite, never raw `git push`). The harness does **not** introduce `git push origin --delete`.
  Instead it keeps the `gt`-mediated remote mutation but fixes the two real defects: (a) it
  ensures the local branch `gt` keys off **still exists** when the remote prune runs by
  reordering so the `gt`-driven remote prune happens **before** local-branch deletion (or by
  re-creating the tracking ref `gt` needs), and (b) it **verifies actual absence** via a
  post-prune `git ls-remote` (a read, allowed) so `removed.remotes` reflects real deletion and
  any still-present ref lands in `failedRemotes`. This supersedes Decision 1 Option A's
  `git push origin --delete` recommendation, which violated the `gt`-only mutation policy.
