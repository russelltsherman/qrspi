---
name: using-graphite-cli
description: "Drive all version-control work — commits, branches, PRs, stacks, conflict resolution — through the Graphite CLI (gt) instead of raw git. Use when creating a branch or commit, submitting or updating a PR, restacking, syncing with trunk, or resolving a stack conflict, or any time you would otherwise reach for git create/commit/rebase/push on a tracked branch."
command: /using-graphite-cli
argument-hint:
allowed-tools: Bash
---

# Using the Graphite CLI (`gt`)

Graphite manages **stacks** of small, dependent branches and their PRs. Each
branch carries exactly one commit and one PR; `gt` tracks the parent/child
relationships so you can amend a lower branch and have everything above it
restack automatically. Use `gt` for every history-changing operation — do not
mix raw `git` branch/commit/rebase commands into tracked branches (see Hard
rules below).

This is general-purpose graphite guidance. For the full command catalog and
flags, see `references/command-reference.md`. For conflict and stack-repair
flows, see `references/conflict-resolution.md`.

## The core loop: Create → Submit → Modify → Sync

This is the everyday workflow. Each step has an agent-default form that runs
without opening an editor or blocking on a prompt.

1. **Create** a branch with its one commit:

   ```
   gt create --all -m "concise message"
   ```

   `--all` stages every tracked change; `-m` supplies the message so no editor
   opens. This cuts a new branch stacked on the current one and commits in a
   single step.

2. **Submit** the branch (and everything upstack) as PRs:

   ```
   gt submit --no-edit --publish
   ```

   `gt ss` is the alias. **Agent submit defaults are `--no-edit --publish`:**
   `--no-edit` reuses the commit message instead of opening the PR-body editor,
   and `--publish` opens a ready PR rather than a draft. Add
   `--reviewers <user>` / `--team-reviewers <team>` to route it to a review
   queue.

3. **Modify** the current branch when you need to change it — amend in place,
   never add a second commit:

   ```
   gt modify --all
   ```

   This folds new changes into the branch's existing commit AND restacks every
   descendant. Re-run `gt submit --no-edit --publish` afterward to update the PR.

4. **Sync** with trunk to pull the latest, restack onto it, and clean up merged
   branches:

   ```
   gt sync
   ```

   Use `gt sync --no-interactive` for autonomous runs so the merged-branch
   cleanup does not prompt.

Loop: create the next branch on top, submit, modify as review comes in, sync
when trunk moves or work merges.

## Stack navigation & directionality

Think of the stack as a vertical line rooted at trunk:

- **downstack = toward trunk** — the parent / older branches, *below* you.
- **upstack = away from trunk** — the child / newer branches, *above* you.

| Command | Moves |
|---------|-------|
| `gt up` / `gt bu` | up one branch (upstack, away from trunk) |
| `gt down` / `gt bd` | down one branch (downstack, toward trunk) |
| `gt stack top` | to the topmost branch (furthest upstack) |
| `gt log short` | print a compact one-line-per-branch view of the whole stack |

Use `gt log short` to see where you are before navigating, then `gt bu` / `gt bd`
to walk the stack and `gt stack top` to jump to the tip.

## Hard rules

Each rule is mandatory. Read the rationale — these prevent the specific failure
modes that desync Graphite's metadata from your actual branch state.

- **One commit per branch — ALWAYS.** Each Graphite branch must hold exactly one
  commit, because a branch maps one-to-one to a PR and Graphite restacks per
  branch; multiple commits per branch break that mapping and muddy review.

- **NEVER run `git rebase` on a tracked branch.** Use `gt restack` / `gt modify`
  / `gt sync` instead, because raw rebase rewrites history without updating
  Graphite's parent/child metadata, leaving the stack pointing at stale parents.

- **NEVER run `git commit --amend` on a tracked branch.** Use `gt modify --all`,
  because amend changes the commit but does not restack the descendants, so every
  branch above it silently desyncs.

- **NEVER run `git rebase --continue` to resolve a Graphite conflict.** Use
  `gt continue` after staging your resolution, because Graphite drives the
  restack internally and reaching past it to raw git corrupts the stack metadata.
  See `references/conflict-resolution.md`.

- **Do NOT mix raw `git push` / `git branch` with tracked branches.** Let
  `gt submit` push and `gt create` branch, because Graphite owns the branch
  topology and out-of-band git operations leave it inconsistent.

The one allowed raw-git step is `git add <file>` to stage a hand-resolved
conflict before `gt continue`.

## Conflict resolution

When `gt create` / `gt modify` / `gt sync` / `gt move` hits a merge conflict,
Graphite pauses. Resolve the files, `git add` them, then run **`gt continue`**
(NEVER `git rebase --continue`). Full flow, edge cases, and stack-repair recipes:
see `references/conflict-resolution.md`.

## QRSPI orchestration differs

This skill documents general-purpose Graphite usage. The QRSPI orchestrator in
this repo (`qrspi-work` / `qrspi-batch.js`) layers stricter, QRSPI-specific
conventions on top — e.g. it runs `gt` non-interactively everywhere, holds the
whole stack open until the feature is approved, and defers `gt sync` until land
rather than syncing mid-feature. Where the orchestrator's rules conflict with the
general defaults here, follow the orchestrator for QRSPI tickets and this skill
for everything else.
