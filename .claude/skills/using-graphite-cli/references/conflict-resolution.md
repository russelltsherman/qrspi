# Conflict Resolution

## Golden Rule

**Always use gt continue, never git rebase --continue.** The Graphite CLI manages stack metadata that git rebase --continue does not understand. Using raw git rebase during a restack will break stack tracking.

## Conflict Resolution During `gt restack`

When `gt restack` encounters conflicts:

1. Stop — let `gt restack` report the conflict locations
2. Resolve conflicts in the affected files using your editor
3. Stage resolved files: `git add <resolved-files>`
4. Run: `gt continue`
5. Repeat from step 2 if more conflicts exist
6. After successful restack, verify with: `gt log short --no-interactive`

## Conflict Resolution During `gt sync`

When `gt sync` encounters conflicts:

1. `gt sync` pauses and reports conflicting files
2. Resolve each conflict in your editor
3. Stage resolved files: `git add <resolved-files>`
4. Run: `gt continue`
5. After successful sync, verify with: `gt log short --no-interactive`

## Conflict Resolution During `gt move`

When `gt move --onto` encounters conflicts:

1. `gt move` pauses and reports conflicting files
2. Resolve each conflict in your editor
3. Stage resolved files: `git add <resolved-files>`
4. Run: `gt continue`
5. After the move completes, verify stack structure with: `gt log short --no-interactive`

## Recovery from Common Errors

### Detached HEAD state
If the worktree ends up in a detached HEAD:
1. Identify the intended branch: `gt log short --no-interactive`
2. Switch back to the branch: `gt checkout <branch-name> --no-interactive`

### Dirty worktree during mutation
If `gt create`, `gt modify`, `gt move`, or `gt restack` fails due to uncommitted changes:
1. Stash changes temporarily: `git stash push -m "temporary stash"`
2. Re-run the command
3. Re-apply stash if needed: `git stash pop`

### Failed restack
If `gt restack` fails irrecoverably:
1. Abort: `gt restack --abort`
2. Assess what changed with `git status`
3. Consider using `gt move --onto` as an alternative if appropriate

## When to Abort vs. Continue

- **Continue** when: you understand the conflict, can resolve it, and the restack/move/sync operation is necessary
- **Abort** when: the conflict reveals a deeper architectural issue, you cannot resolve it without losing work, or the operation was unintended

Use `gt <operation> --abort` to abort the current operation (e.g., `gt restack --abort`, `gt sync --abort`).
