# Design — Deterministic worktree & branch cleanup for fully-merged QRSPI stacks

**Ticket:** RUS-52
**Research basis:** research.md @ 2026-06-07T00:00:00Z
**Generated:** 2026-06-07T00:00:00Z
**Status:** draft

## Current State

Cleanup of a landed ticket's worktree and branches is today natural-language PROSE in a single LAND worker `agent(...)` prompt, which delegates to the `action: land` steps of `qrspi-work/SKILL.md`; there is no dedicated cleanup Python script (ref: Q1). That prose runs `gt merge --confirm`, `gt sync --force` (which deletes merged branches and prunes remotes), `git worktree remove --force 2>/dev/null`, and `git worktree prune` (ref: Q5, Q9). Removal is unconditionally forced and suppresses errors, so it SWALLOWS the "worktree has uncommitted changes" safety error git would raise — there is no programmatic dirty-state guard before destruction (ref: Q9).

Merge state is unmodeled. `qrspi_pr_state.py` enumerates a stack's PRs via `git branch --list "<ticket>/*"`, gates each branch through `real_branches()` (≥1 commit ahead of trunk), and queries GitHub GraphQL with `states:OPEN` only — it reports `prExists`/`number`/`reviewDecision`/`unresolvedThreads` but has NO `merged`/`state`/`mergedAt` field and no visibility into MERGED or CLOSED PRs (ref: Q2). The resolver classifies on `reviewDecision`/`unresolvedThreads` and likewise cannot distinguish merged from closed-unmerged; a merged PR simply disappears from the OPEN query (ref: Q7).

The harness keeps NO persistent registry of in-flight vs finished tickets; truth is recomputed live each run from git refs, `os.path.isdir(worktree)`, and Linear status (ref: Q8). The batch QUERY phase sweeps only `Selected`/`*Review` statuses — `Done` is never swept, so a finished-but-uncleaned ticket is invisible to reconciliation today (ref: Q8). Worktree path is always `<repo>/.worktrees/<ticket>` and branch names are `<ticket>/{design,plan,slice-N}`; `worktree_path`, `pick_tip`, `slice_numbers`, and `branch_set` already derive these and are reusable (ref: Q3).

All three existing self-locating scripts share one contract: derive `REPO_ROOT` from `__file__` (two levels up), `argparse` with `--ticket`, emit exactly one stdout JSON envelope with `ok`/`repoRoot`/`error?`, exit 0/1, and report any infra error ONCE as `ok:false` without retrying (ref: Q4). They are structurally idempotent — missing worktree/branch is treated as a clean no-op success, and re-runs reconcile partial work (ref: Q11, Q12). No script exposes a `--dry-run` flag today; the closest idiom is the resolver's pure decide-then-act split (ref: Q6). Tests are stdlib-only with NO subprocess mocking: logic is split into a pure data-in/data-out layer (unit-tested with plain dict / rc-stdout-stderr fixtures) and a thin subprocess layer (manual e2e only) (ref: Q13, Q14). Operator visibility flows through the resolver `decision.reason`, batch `log(...)` lines, per-ticket result `summary`, and each script's stdout envelope (ref: Q15).

## Desired End State

A new deterministic, self-locating, stdlib-only, unit-tested script `scripts/qrspi_cleanup.py` reaps a ticket's worktree, local stack branches, and merged remote refs once — and only once — its entire stack has merged.

- **AC1:** When every PR in a ticket's stack is merged, the script removes its worktree, local stack branches, and merged remote refs with no manual steps — invoked automatically inside `doLand` after the bottom-up merge.
- **AC2:** The pure decision function returns `skip` (untouched) whenever ANY stack PR is unmerged or still in-review — strictly all-or-nothing per stack (built on a new MERGED-aware GraphQL query, ref: Q2, Q7).
- **AC3:** A worktree with uncommitted changes yields a `blocked` decision (never destroyed); the dirty state is surfaced in the envelope `error`/`reason`, replacing today's `--force 2>/dev/null` (ref: Q9).
- **AC4:** Cleanup runs automatically on land, AND a new reconciliation pass in `qrspi-batch.js` enumerates already-merged-but-uncleaned tickets and reaps them (ref: Q1, Q8).
- **AC5:** Running the reconciliation against the current repo clears the existing backlog of stranded merged worktrees/branches (the 27 worktrees / 20+ merged stacks).
- **AC6:** Cleanup decisions key on authoritative PR merge state from GitHub and are covered by automated tests for merged / partially-merged / dirty / in-flight cases (ref: Q13, Q14).

## Delta

- **New file `scripts/qrspi_cleanup.py`** — self-locating one-shot script matching the established contract (ref: Q4). Pure layer: `classify_cleanup(stack_merge_state, dirty_porcelain)` → `{decision: destroy|skip|blocked, reason}`. Impure layer: gather merge state, run `git status --porcelain` (ref: Q9), and on `destroy` execute removal + pruning behind a `--dry-run` gate (ref: Q6). Reuses `worktree_path`, `branch_set`, `slice_numbers`, `pick_tip` (ref: Q3). Emits one envelope: `ok`, `repoRoot`, `decision`, `reason`, `removed{worktree,branches,remotes}`, `error?`.
- **New file `scripts/qrspi_cleanup_test.py`** — stdlib-only, assert/`check()` style (majority convention), dict/text fixtures for merged/partial/dirty/in-flight, NO mocks (ref: Q13, Q14).
- **Modified `scripts/qrspi_pr_state.py`** — extend the GraphQL query to surface merge state (add a MERGED-aware query or a `state`/`merged`/`mergedAt` field), since the OPEN-only query cannot answer "is this stack fully merged?" (ref: Q2, Q7). Add a pure helper exposing per-branch merged booleans for the stack.
- **Modified `.claude/workflows/qrspi-batch.js`** — (a) in `doLand`, replace the prose worktree/branch removal with a verbatim one-command invocation of `qrspi_cleanup.py` after the merge succeeds (ref: Q1, Q15); (b) add a reconciliation pass that lists candidate finished tickets and runs cleanup against each, folding outcomes into the results array (ref: Q8, Q15).
- **Modified `.claude/skills/qrspi-work/SKILL.md`** — replace the `gt sync --force` / `git worktree remove --force` land-cleanup prose with the script invocation (ref: Q1, Q5).

## Pattern Decisions

### Decision 1: How to detect "fully merged" stack

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Extend `qrspi_pr_state.py` GraphQL to include MERGED state per branch; cleanup consumes a pure stack-merged predicate | Reuses existing stack enumeration + `real_branches`; one authoritative gatherer; testable pure predicate | Touches a shared, tested file; must keep OPEN-path callers unaffected |
| B | New standalone GraphQL gatherer inside `qrspi_cleanup.py` | Isolated; no risk to existing callers | Duplicates branch enumeration / `real_branches` logic; two divergent PR-state sources |

**Recommendation:** Option A
**Rationale:** `qrspi_pr_state.py` is already the single PR-state gatherer with tested pure parsers and the `real_branches`/`slice_numbers` machinery; the OPEN-only query is the documented gap, and extending it keeps one authoritative merge-state source (ref: Q2, Q7).
**NEW PATTERN?** No — extends the existing gatherer and pure-parser convention.

### Decision 2: Dirty-worktree safety

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `git status --porcelain`; non-empty ⇒ `blocked` decision, never remove | Honors AC3; surfaces instead of forcing; pure-classifiable from porcelain text | One extra subprocess per ticket |
| B | Keep `git worktree remove --force` | Simplest; matches today | Violates AC3 — silently discards uncommitted work (ref: Q9) |

**Recommendation:** Option A
**Rationale:** Today's `--force 2>/dev/null` swallows the exact safety error AC3 requires; a porcelain check feeds a pure `blocked` classifier mirroring `classify_result(rc, stdout, stderr)` (ref: Q9, Q14).
**NEW PATTERN?** No — same pure-classifier shape as restack.

### Decision 3: Remote ref pruning mechanism

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Prune via `gt sync --force` (the sanctioned land-cleanup command) | Consistent with harness; constraint forbids direct destructive remote ops; tolerant of already-deleted refs | `gt sync` only legal at land, not mid-feature (ref: Q5) |
| B | Direct `git push --delete` per remote branch | Precise | Violates the "remote pruning through Graphite" constraint (ref: Q5) |

**Recommendation:** Option A
**Rationale:** Cleanup runs only at/after land, the one lifecycle moment `gt sync` is permitted, and GitHub auto-deletes merged head refs so pruning must tolerate missing refs as no-op success (ref: Q5, Q11).
**NEW PATTERN?** No — same `gt`-only remote rule as the rest of the harness.

### Decision 4: Dry-run / preview

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `--dry-run` flag gating only the destructive execution; decision computed identically | Satisfies "safe to preview"; pure decision stays testable; lets operators clear the backlog cautiously | First script to add such a flag |
| B | No preview; rely on idempotency | Less code | Fails the preview constraint; risky for the AC5 backlog sweep |

**Recommendation:** Option A
**Rationale:** No script has `--dry-run` today, but the constraints explicitly require safe-to-preview, and the pure decide-then-act split already in the resolver makes gating the act trivial (ref: Q6).
**NEW PATTERN?** Yes — first `--dry-run` flag; justified because the existing decide-then-act split has no preview surface and the backlog sweep (AC5) needs one. Establishes the convention for future destructive scripts.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Backlog sweep destroys a worktree wrongly judged "merged" due to GraphQL paging/state bug | low | high | Pure merged-predicate unit-tested; `--dry-run` preview before the real AC5 sweep; all-or-nothing gate (ref: Q6, Q13) |
| Extending `qrspi_pr_state.py` query breaks existing OPEN-path resolver/restack callers | med | high | Add merge field additively; keep existing fields; rerun `qrspi_pr_state_test.py` + resolver tests (ref: Q2, Q14) |
| Reconciliation can't find finished tickets — batch sweeps only `Selected`/`*Review`, never `Done` (ref: Q8) | med | med | Drive reconciliation from git/GitHub (worktree dirs + merged PRs), not Linear status, consistent with "truth is live from git" (ref: Q8) |
| Partial merge mid-sweep leaves stack half-reaped | low | high | Strict all-or-nothing in the pure classifier (AC2); destroy only when every real branch's PR is merged (ref: Q7) |
| `gt sync --force` errors on already-deleted remote refs | med | low | Treat absent refs / missing worktree as clean no-op success per existing idempotency idiom (ref: Q11, Q12) |

## Open Questions

- OQ1: For the AC5 backlog sweep, should reconciliation enumerate candidates from `.worktrees/*` directories on disk, from merged PRs on GitHub, or the intersection? (Batch Linear sweep won't see `Done` tickets — ref: Q8.)
- OQ2: Should a `blocked` (dirty) ticket during the batch reconciliation pass halt the run or just be logged and skipped while others proceed? Existing actions record failures and continue (ref: Q15).
- OQ3: For the merge-state query, is matching on `headRefName` with `states:MERGED` sufficient, or must we also reconcile branches GitHub already deleted (no open or merged PR returned by head ref)? (ref: Q2, Q11)
- OQ4: Should `--dry-run` be the default for the standalone CLI (opt-in to destroy) given the proven path-mangling worker risk, even though `doLand` always passes the destroy flag?
