---
name: using-git-worktrees
description: Guidance for using Git worktrees correctly — set up a bare-repo-primary layout, run several worktrees in parallel without collisions, and handle the full create/work/PR/merge/remove/prune lifecycle. Use whenever someone wants to work on multiple branches at once, run parallel agents on isolated checkouts, set up or bootstrap a bare repo for worktrees, or asks about worktree isolation (per-worktree .env, ports, dependencies), cleanup, or worktree gotchas (submodules, the shared stash).
command: /using-git-worktrees
argument-hint: "[topic, e.g. setup | isolation | cleanup]"
allowed-tools: Read, Bash, Glob, Grep
---

# Using Git Worktrees

Git worktrees let one repository have several working directories backed by a
single shared object store — the practical way to work multiple branches at once
(e.g. parallel agents, each on its own branch and PR) without re-cloning.

Lead use case: **a bare-repo-primary layout with one worktree per branch/ticket
so no checkout is privileged and agents never collide.** This body is the thin
procedure; load `references/worktrees.md` for the full detail on any step.

## Procedure

### 1. Set up the base (bare-repo-primary)

Bootstrap a bare clone (object store in `.bare/`), a `.git` pointer, the fetch
refspec a bare clone omits, and a first worktree — all via the bundled script:

```bash
.claude/skills/using-git-worktrees/scripts/bootstrap-bare-repo.sh \
  <repo-url> [target-dir]
```

Resulting layout (`.bare/` + a `.git` pointer file + one directory per worktree)
and the reason the fetch-refspec step is mandatory are in
`references/worktrees.md` §1. You do **not** need a bare repo to use worktrees —
an ordinary clone can `git worktree add` too; this repo's own harness uses that
linked-from-`main` model, putting each ticket's worktree under the gitignored
`.worktrees/<ticket-id>/`. Pick bare-primary when no checkout should be
privileged; pick linked-from-a-normal-clone when you already have one. Both are
covered in `references/worktrees.md` §1.

### 2. Create a worktree per branch

```bash
git worktree add -b <branch> <dir>   # new branch + checkout
git worktree add <dir> <branch>      # existing branch
git worktree add --detach <dir> <ref>  # throwaway/read-only checkout
```

One branch per worktree — Git refuses the same branch in two worktrees. Full
lifecycle (create → work → PR → merge → remove → prune) in
`references/worktrees.md` §2.

### 3. Isolate parallel worktrees

A new worktree only materializes **tracked** files, so per-worktree state must be
set up deliberately:

- Copy/create `.env` per worktree — it does not propagate.
- Give each worktree a distinct port via a gitignored `.env.local` override.
- Install dependencies per worktree (`node_modules/`, `.venv/`, … are not shared).
- Keep to **3–5 concurrent worktrees**; retire finished ones before opening new.

Details and rationale (including why symlinking `node_modules` is fragile) in
`references/worktrees.md` §3; what is shared vs per-worktree in §4.

### 4. Tear down and maintain

```bash
git worktree remove <dir>     # after the branch is merged (add --force to discard changes)
git branch -d <branch>        # remove removes the worktree, not the branch
git worktree prune            # clear stale entries after a manual rm -rf
git worktree list             # source of truth for what exists
```

Maintenance and CI/review integration in `references/worktrees.md` §5–§6.

## Watch out for

- **The stash is shared** across all worktrees — a stash pushed in one is
  poppable (into the wrong tree) from another. Use a WIP commit instead.
- **Submodules** are not reliably isolated or initialized per worktree — run
  `git submodule update --init --recursive` in each new worktree.
- **`.git` is a file** (a `gitdir:` pointer), not a directory, in worktrees and
  in the bare-primary top level.

Full gotchas list in `references/worktrees.md` §7.
