# Git Worktrees — Full Reference

Long-form companion to `SKILL.md`. Covers the bare-repo-primary layout, the full
worktree lifecycle, parallel-agent isolation, shared state/config, cleanup and
maintenance, CI/review integration, and the gotchas that bite (submodules and the
shared stash).

---

## 1. Bare-repo-primary layout

A *worktree* is a second (third, …) working directory backed by **one** shared
`.git` object store. The cleanest base for many worktrees is a **bare clone** that
holds only the repository database, with every checkout living as a worktree
beside it. Nothing has to live "in" a primary checkout, so no single branch is
privileged.

```
my-project/
├── .bare/                  # the bare object store (the real repository)
├── .git                    # one-line pointer file: "gitdir: ./.bare"
├── main/                   # worktree checked out to main
├── feature-x/              # worktree checked out to feature-x
└── RUS-42/                 # worktree for a ticket branch
```

The `.git` pointer (a file, not a directory) makes plain `git` commands run from
`my-project/` resolve to `.bare/`, so `git worktree list` and friends work from
the top level.

### Bootstrap it

Use the bundled script — it does the bare clone, writes the `.git` pointer,
configures the fetch refspec a bare clone omits, fetches, and adds the first
worktree:

```bash
.claude/skills/using-git-worktrees/scripts/bootstrap-bare-repo.sh \
  https://github.com/owner/repo.git my-project
```

Run with no arguments to see the usage guard:

```bash
.claude/skills/using-git-worktrees/scripts/bootstrap-bare-repo.sh
# error: ... Usage: bootstrap-bare-repo.sh <repo-url> [target-dir]
```

### Why the fetch refspec step matters

`git clone --bare` sets **no** `remote.origin.fetch` refspec, so a later
`git fetch` would not populate `refs/remotes/origin/*`. The script sets:

```
remote.origin.fetch = +refs/heads/*:refs/remotes/origin/*
```

so remote-tracking branches behave exactly as they would in a normal clone. This
is the single most common reason a hand-rolled bare setup "can't see" remote
branches.

### Alternative: worktrees from an ordinary clone

You do **not** need a bare repo to use worktrees. Any normal clone can spawn
worktrees with `git worktree add`; the new checkout lands wherever you point it
(commonly a sibling `../` directory or a gitignored subdirectory). This repo's
QRSPI harness uses exactly this model: the primary checkout stays on `main` and
each ticket gets a linked worktree under `.worktrees/<ticket-id>/` (which is
gitignored). The bare-repo layout above is the more symmetric option when *no*
checkout should be privileged; the linked-from-a-normal-clone model is simpler
when you already have a primary checkout. The lifecycle, isolation, and cleanup
guidance below applies to both.

---

## 2. Full lifecycle: create → work → PR → merge → remove → prune

### Create

```bash
# New branch + worktree in one step (branch created off current HEAD):
git worktree add -b feature-x feature-x

# Worktree for an existing local or remote branch:
git worktree add feature-x feature-x

# Detached worktree at a specific commit (e.g. to bisect or build a tag):
git worktree add --detach hotfix-check v1.4.2
```

Each worktree gets its own `HEAD`, index, and checked-out files, but shares the
object store, refs, config, and stash with every sibling.

### Work

`cd` into the worktree and use git normally — commit, branch, rebase. The one
hard rule: **the same branch cannot be checked out in two worktrees at once.**
Git refuses with `fatal: '<branch>' is already checked out at '<path>'`. Use a
distinct branch per worktree, or `--detach` for a throwaway checkout.

### PR

Push and open the PR from inside the worktree, same as any checkout. If you use
the Graphite CLI, run `gt` from within the worktree; it operates on that
worktree's branch. Requesting reviewers is what surfaces the PR in a reviewer's
queue.

### Merge

Merge via the PR (or `gt merge` for a stack). The merge happens on the remote and
in the shared object store — no per-worktree action is needed beyond syncing.

### Remove

Once the branch is merged, retire the worktree:

```bash
git worktree remove feature-x          # refuses if there are uncommitted changes
git worktree remove --force feature-x  # discard the working tree anyway
```

`remove` deletes the worktree directory and its administrative entry. It does
**not** delete the branch — do that separately (`git branch -d feature-x`).

### Prune

If a worktree directory was deleted manually (e.g. `rm -rf`), its bookkeeping
under `.git/worktrees/` lingers. Clean it up:

```bash
git worktree prune        # drop entries whose directories are gone
git worktree list         # confirm the survivors
```

---

## 3. Parallel-agent isolation

Worktrees are how multiple agents (or humans) work different branches
concurrently without stepping on each other. Each worktree is a separate working
directory, so checked-out files, the index, and `HEAD` are isolated. But several
things are **not** automatically isolated and need deliberate handling.

### Per-worktree environment files

`.env` (and similar untracked config) does **not** propagate to a new worktree —
`git worktree add` only materializes tracked files. Each worktree needs its own:

```bash
cp main/.env feature-x/.env     # seed from an existing worktree
# then edit feature-x/.env for this worktree's specifics
```

Treat `.env` as per-worktree state, never shared.

### Port overrides via .env.local

Two agents running the same dev server will collide on a port. Give each worktree
its own port through a per-worktree override (e.g. `.env.local`, which most
frameworks load after `.env` and which should be gitignored):

```bash
# feature-x/.env.local
PORT=3001

# feature-y/.env.local
PORT=3002
```

Keep a simple convention (e.g. one port band per worktree) so collisions are
impossible by construction.

### Independent dependency installation

Package directories (`node_modules/`, `.venv/`, `target/`, `vendor/`) are
build artifacts, not tracked files, so a new worktree starts without them. Install
per worktree:

```bash
cd feature-x && npm install      # or: uv sync / pip install / cargo build
```

Symlinking a shared `node_modules` across worktrees is tempting but fragile —
native modules and lockfile drift between branches cause subtle, hard-to-debug
breakage. Prefer an independent install per worktree; use a shared package cache
(npm/pnpm store, pip wheel cache) for speed instead.

### Keep the worktree count small

Each active worktree is a full checkout plus its own dependencies and running
processes — disk, file watchers, and ports add up fast. A practical ceiling is
**3–5 concurrent worktrees**. Beyond that, retire finished ones before opening
new ones rather than accumulating stale checkouts.

---

## 4. Shared state and config

Everything in the object store is shared across worktrees — this is the point,
but know the seams:

- **Objects, refs, branches, tags** — shared. A commit made in one worktree is
  immediately visible to all.
- **`config`** — shared (one `.git/config`). Per-worktree overrides are possible
  with `git config --worktree <key> <value>` **after** enabling
  `git config extensions.worktreeConfig true`.
- **Hooks** — shared (`.git/hooks` is common to all worktrees).
- **The stash** — shared (see Gotchas). A stash pushed from one worktree is
  visible — and poppable — from every other.
- **`HEAD`, index, `MERGE_HEAD`, an in-progress rebase/merge** — per-worktree.

---

## 5. Cleanup and maintenance

- After merging a branch, `git worktree remove` its worktree and delete the
  branch; don't let dead checkouts pile up.
- Run `git worktree prune` periodically (and always after manually deleting a
  worktree directory) to clear stale `.git/worktrees/` entries.
- `git worktree list` is the source of truth for what exists; reconcile it with
  what's on disk.
- A `locked` worktree (e.g. on removable media) is skipped by `prune`; unlock
  with `git worktree unlock <path>` before removing.
- Garbage collection (`git gc`) on the shared store benefits every worktree at
  once — run it on the bare repo / primary checkout.

---

## 6. CI / review integration

- Worktrees are a **local** workflow; CI sees only the branch you push. Nothing
  about a worktree layout changes what lands on the remote.
- Push and open PRs from inside the relevant worktree so the PR tracks that
  worktree's branch. With Graphite, run `gt submit` from the worktree.
- A worktree-per-ticket layout maps one worktree → one branch → one PR, which
  keeps concurrent reviews cleanly separated.
- CI config (workflow files) is tracked and therefore shared across worktrees —
  edit it in whichever worktree owns that change, like any other tracked file.

---

## 7. Gotchas

### Submodules

Submodules and worktrees interact poorly. Submodule working state is **not**
fully isolated per worktree, and `git worktree add` does not reliably initialize
submodules in the new checkout. After adding a worktree in a superproject:

```bash
cd new-worktree
git submodule update --init --recursive
```

Expect to manage submodule checkouts per worktree by hand, and be wary of running
submodule-mutating commands in parallel across worktrees.

### The shared stash

`git stash` is **global to the repository**, not per-worktree. A stash you push
in `feature-x` appears in `git stash list` from `feature-y` — and popping it
there applies it to the wrong working tree, often with conflicts. Avoid `stash`
as a cross-worktree carry mechanism. Prefer a WIP commit (`git commit -m wip`,
amend/undo later) for parking changes, since commits are branch-scoped and won't
leak into another worktree.

### Same branch in two worktrees

Git forbids checking the same branch out twice. This is a feature — it prevents
two working trees from fighting over one branch ref. Use distinct branches, or
`--detach` for a read-only/throwaway checkout.

### The .git pointer is a file

In a worktree (and in the bare-repo layout's top level), `.git` is a **file**
containing a `gitdir:` line, not a directory. Tools that assume `.git/` is a
directory can misbehave — point them at the resolved git dir if needed.
