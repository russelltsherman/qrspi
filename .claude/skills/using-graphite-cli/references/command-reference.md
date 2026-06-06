# Graphite CLI Command Reference

Full `gt` command catalog with the flags this skill relies on. The body
(`SKILL.md`) documents the everyday Create → Submit → Modify → Sync loop; this
file is the lazy-loaded catalog for flags and less-common commands. Run
`gt <command> --help` for the authoritative, version-specific flag list.

## Create — start a new branch on top of the current one

`gt create` cuts a new branch stacked on the current branch and commits the
staged (or all) changes in one step.

| Invocation | Effect |
|------------|--------|
| `gt create --all -m "msg"` | Stage every tracked change, create a branch, commit with `msg`. The default agent flow. |
| `gt create <name> --all -m "msg"` | Same, with an explicit branch name instead of one derived from the message. |
| `gt create -m "msg"` | Commit only what is already staged (no `--all`). |

- `--all` / `-a` — stage all tracked changes before committing.
- `-m "msg"` — commit message. Always pass one in non-interactive agent runs so
  no editor opens.
- One `gt create` == one branch == one commit. Keep it that way (see the
  single-commit-per-branch hard rule in `SKILL.md`).

## Submit — publish the branch/stack as PRs

`gt submit` (alias `gt ss` for "stack submit") pushes branches and opens or
updates their PRs.

| Invocation | Effect |
|------------|--------|
| `gt submit --no-edit --publish` | Agent default: push current upstack, create/update PRs, skip the description editor, publish (not draft). |
| `gt ss --no-edit --publish` | Same via the stack-submit alias. |
| `gt submit --stack` | Submit the entire stack, not just the current branch and up. |
| `gt submit --draft` | Open PRs as drafts instead of published. |
| `gt submit --reviewers <user,...>` | Request the named user reviewers. |
| `gt submit --team-reviewers <team,...>` | Request the named team reviewers. |

- `--no-edit` — do not open an editor for the PR body; use the commit message.
- `--publish` — open as a ready PR rather than a draft.
- Requesting a reviewer is what surfaces the PR in that reviewer's queue.

## Modify — amend the current branch's commit

`gt modify` folds new changes into the current branch's existing commit and
automatically restacks everything above it.

| Invocation | Effect |
|------------|--------|
| `gt modify --all` | Stage all tracked changes and fold them into the current branch's commit; restack upstack. The agent default for "edit this branch". |
| `gt modify --all -m "new msg"` | Same, and replace the commit message. |
| `gt modify --commit` | Add a *new* commit instead of amending (avoid — breaks single-commit-per-branch). |

- Prefer `gt modify --all` over `git commit --amend`: it amends AND restacks the
  descendants, which raw git will not do.

## Sync — pull trunk and clean up merged branches

`gt sync` pulls the latest trunk, restacks your branches onto it, and offers to
delete branches whose PRs have merged.

| Invocation | Effect |
|------------|--------|
| `gt sync` | Fetch trunk, restack, prompt to delete merged branches. |
| `gt sync --no-interactive` | Same without prompts — safe for autonomous agents. |
| `gt restack` | Restack the current stack onto its parents without fetching trunk. |

## Navigation — move around the stack

Directionality: **downstack = toward trunk** (older/parent branches),
**upstack = away from trunk** (newer/child branches).

| Command | Effect |
|---------|--------|
| `gt up` / `gt bu` | Check out the child branch (move upstack, away from trunk). |
| `gt down` / `gt bd` | Check out the parent branch (move downstack, toward trunk). |
| `gt top` / `gt stack top` | Jump to the topmost (furthest upstack) branch. |
| `gt bottom` | Jump to the branch just above trunk. |
| `gt checkout <branch>` / `gt co <branch>` | Jump to a named branch. |

## Log / inspect

| Command | Effect |
|---------|--------|
| `gt log` | Full stack view with commits. |
| `gt log short` / `gt ls` | Compact one-line-per-branch stack view. |
| `gt status` | Current branch, tracking state, and dirty files. |

## Move / reorder

| Command | Effect |
|---------|--------|
| `gt move --onto <branch>` | Reparent the current branch onto a different branch. |
| `gt fold` | Fold the current branch's commit into its parent (merges two branches into one). |
| `gt squash` | Squash the current branch's commits into a single commit. |

## Conflicts

When any restacking operation (`create`, `modify`, `sync`, `move`, `restack`)
hits a merge conflict, Graphite pauses. Resolve the files, stage them, then run
`gt continue` — NEVER `git rebase --continue`. See
`references/conflict-resolution.md` for the full flow.

## Non-interactive note for agents

For autonomous runs, prefer the non-interactive forms (`--no-edit`,
`--publish`, `--no-interactive`, always `-m`) so no command blocks on an editor
or a yes/no prompt.
