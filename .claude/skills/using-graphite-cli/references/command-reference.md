# Graphite CLI Command Reference

All `gt` commands below include `--no-interactive` unless noted otherwise.

## Directionality Conventions

- **Downstack** = toward trunk/main (the base of the stack)
- **Upstack** = away from trunk/main (the tip of the stack)
- A branch that depends on another is "above" or "on top of" it
- `gt move --onto` places the current branch at the tip of another branch (upstack mutation)

## Branch Lifecycle Commands

### `gt create`

Creates a new branch and commits staged changes to it. Must be run from an existing branch.

**Syntax:**
```
gt create <branch-name> --no-interactive -m "commit message"
```

**Flags:**
- `<branch-name>` (required): Name for the new branch
- `-m` (required): Commit message
- `--no-interactive` (required): Skip interactive prompts
- `-a` (forbidden): NEVER use this flag; use explicit `git add` before `gt create`

**Examples:**
```
gt create feature-auth --no-interactive -m "Add JWT validation logic"
```

**Notes:**
- All changes must be staged with `git add` before running `gt create`.
- Each branch gets exactly one commit from `gt create`. Never run `gt create` twice on the same branch.

### `gt modify`

Amends the current branch's commit with new staged changes. For augmenting an existing commit.

**Syntax:**
```
gt modify --no-interactive -m "additional changes"
```

**Flags:**
- `-m` (required): Commit message describing the amend
- `--no-interactive` (required): Skip interactive prompts
- `-a` (forbidden): NEVER use this flag; use explicit `git add` before `gt modify`

**Examples:**
```
gt modify --no-interactive -m "Fix null check in token parser"
```

**Notes:**
- Use `gt modify` when you need to add changes to the current branch's single commit.
- Never run `gt modify` without having staged changes first.

### `gt submit`

Pushes the current stack and creates/updates corresponding pull requests.

**Syntax:**
```
gt submit --no-edit --no-interactive
```

**Flags:**
- `--no-edit` (required): Skip interactive PR title/body editing
- `--no-interactive` (required): Skip all interactive prompts
- `--force` (optional): Force push if branch has diverged from remote

**Examples:**
```
gt submit --no-edit --no-interactive
```

**Notes:**
- Always ask the user for confirmation before running `gt submit`.
- `gt submit` pushes all branches in the current stack.

## Stack Navigation Commands

### `gt bu`

Switch to the branch above (upstack) in the current stack.

**Syntax:**
```
gt bu --no-interactive
```

### `gt bd`

Switch to the branch below (downstack) in the current stack.

**Syntax:**
```
gt bd --no-interactive
```

### `gt stack top`

Display the top-most branch of the current stack without switching.

**Syntax:**
```
gt stack top --no-interactive
```

### `gt checkout`

Checkout a specific branch in the stack by name or index.

**Syntax:**
```
gt checkout <branch-name-or-index> --no-interactive
```

## Stack Management Commands

### `gt log`

Display a full visualization of the current branch stack.

**Syntax:**
```
gt log --no-interactive
```

### `gt log short`

Display a compact single-line summary of the current stack.

**Syntax:**
```
gt log short --no-interactive
```

**Examples:**
```
$ gt log short --no-interactive
* feature-auth (HEAD)  a1b2c3d Add JWT validation
* main                 e5f6g7h Initial project setup
```

### `gt move`

Move the current branch to stack on top of another branch.

**Syntax:**
```
gt move --onto <target-branch> --no-interactive
```

**Flags:**
- `--onto` (required): Target branch to place current branch on top of
- `--no-interactive` (required): Skip interactive prompts

**Examples:**
```
gt move --onto feature-base --no-interactive
```

### `gt restack`

Restack the current branch (and optionally upstack branches) onto a new base.

**Syntax:**
```
gt restack <target-branch> --no-interactive
```

**Flags:**
- `<target-branch>` (required): New base branch to restack onto
- `--no-interactive` (required): Skip interactive prompts

### `gt delete`

Delete a branch from the stack.

**Syntax:**
```
gt delete <branch-name> --no-interactive
```

**Flags:**
- `<branch-name>` (required): Branch to delete
- `--no-interactive` (required): Skip confirmation prompts

## Sync Commands

### `gt sync`

Pull latest changes from the default branch and sync the stack.

**Syntax:**
```
gt sync --force --delete-all --no-interactive
```

**Flags:**
- `--force` (required): Rebase onto latest default branch even if diverged
- `--delete-all` (optional): Delete all merged remote branches after sync
- `--no-interactive` (required): Skip interactive prompts

**Examples:**
```
gt sync --force --delete-all --no-interactive
```

**Notes:**
- Check `git status` before running `gt sync` to ensure no uncommitted changes.
- `--delete-all` removes branches that have been merged into the default branch.

## `gt continue`

Resolves merge conflicts during restack or sync operations. Detailed procedures are documented in `references/conflict-resolution.md`. Do not use `git rebase --continue` — always use `gt continue` instead.
