# Conflict Resolution & Stack Repair

This file is the lazy-loaded companion to `SKILL.md`. It covers what to do when
a Graphite operation pauses on a conflict, plus a few stack-repair recipes.

## The canonical conflict step: `gt continue`

Any restacking operation — `gt create`, `gt modify`, `gt sync`, `gt move`,
`gt restack` — replays your commits onto new parents. If a replay hits a merge
conflict, Graphite stops and tells you which files conflict.

**Resolve a Graphite conflict with `gt continue` — NEVER `git rebase --continue`.**
Graphite drives the restack internally; reaching past it to raw git desyncs
Graphite's metadata from the actual branch state and can corrupt the stack.

### Flow

1. Graphite pauses and prints the conflicting files.
2. Open each conflicting file and resolve the `<<<<<<< / ======= / >>>>>>>`
   markers by hand (or with your merge tool).
3. Stage the resolved files: `git add <file>` (staging the resolution is the one
   raw-git step that is expected here).
4. Continue the operation: `gt continue`.
5. If more conflicts surface further up the stack, repeat steps 2–4 until
   `gt continue` reports the operation is complete.

### Aborting

- `gt continue --abort` (or the abort option Graphite offers in its prompt)
  unwinds the in-progress restack and returns you to the pre-operation state.
- Prefer Graphite's own abort over `git rebase --abort` for the same metadata
  reason as above.

## Edge cases

- **Empty resolution.** If resolving a conflict leaves the commit empty (all
  changes already present upstream), Graphite will tell you; follow its prompt to
  drop or keep the now-empty commit rather than forcing it through with raw git.
- **Conflict during `gt sync`.** Trunk moved under you. Resolve, `git add`,
  `gt continue`; the rest of the stack restacks onto the new trunk afterward.
- **Conflict during `gt modify`.** Your amend conflicts with a descendant.
  Resolve each descendant in turn with `gt continue`; do not `git commit --amend`
  partway through — that orphans the restack.
- **Mid-operation interruption.** If you lose the shell mid-restack, run
  `gt continue` again (or `gt status`) to see where Graphite left off; do not
  start a `git rebase` to "finish it manually".

## Stack-repair recipes

| Symptom | Fix |
|---------|-----|
| Branches show as "needs restack" in `gt log short` | `gt restack` (restack current stack onto its parents). |
| A branch is parented on the wrong base | `gt move --onto <correct-parent>`. |
| Two branches should be one | Check out the upper branch, `gt fold` (folds its commit into the parent). |
| Multiple commits crept onto one branch | `gt squash` to collapse back to one commit per branch. |
| Local stack diverged from remote after manual git | `gt sync` to re-fetch and restack; if metadata is broken, `gt restack`. |

## Why not raw git?

Graphite stores parent/child relationships and PR associations as branch
metadata. `git rebase`, `git commit --amend`, and `git rebase --continue` on a
tracked branch change history without updating that metadata, so Graphite's view
of the stack drifts from reality — later `gt` commands then restack onto stale
parents or fail outright. Always let `gt` perform the history rewrite, and only
reach for raw `git add` to stage a hand-resolved conflict.
