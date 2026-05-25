# Rollback Procedures Reference

Purpose: Detailed guide to undoing ArgoCD deployments — Git revert as the primary approach, emergency ArgoCD rollback, post-rollback reconciliation, and deployment history inspection.

## Rollback Strategy Overview

There are two ways to roll back an ArgoCD-managed deployment:

1. **Git revert (preferred)** — Revert the commit in Git, then sync. This keeps Git and the cluster aligned.
2. **ArgoCD rollback (emergency)** — Use `argocd app rollback` to restore a previous cluster state. This creates Git drift that must be reconciled.

Always prefer Git revert unless Git operations are blocked (repository down, access revoked, urgent time pressure).

## Git Revert (Primary Path)

### Why Git revert is preferred

ArgoCD's operating model is GitOps: Git is the source of truth, and the cluster converges to match Git. When you use `argocd app rollback`, the cluster state diverges from Git. On the next sync (manual or automated), ArgoCD re-applies the Git state — which is the bad version you just rolled back from.

Git revert avoids this by updating Git itself:

1. The revert commit undoes the bad change in Git
2. ArgoCD detects the new commit
3. ArgoCD syncs the reverted state to the cluster
4. Git and cluster remain aligned

### Procedure

```bash
# Step 1: Identify the bad commit
# Check ArgoCD for the revision that caused the issue
argocd app history <app-name>
# Note the Git revision (commit SHA) from the problematic entry

# Step 2: Revert the commit in the application's Git repository
cd <application-git-repo>
git revert <bad-commit-sha>
git push origin main

# Step 3: Sync ArgoCD (if not using automated sync)
argocd app sync <app-name>

# Step 4: Verify the rollback
argocd app get <app-name>
# Confirm: Sync Status = Synced, Health Status = Healthy
```

### Reverting multiple commits

If the bad change spans multiple commits:

```bash
# Revert a range of commits (oldest to newest)
git revert --no-commit <oldest-bad-sha>..<newest-bad-sha>
git commit -m "Revert commits <oldest-bad-sha>..<newest-bad-sha>: <reason>"
git push origin main
```

### Handling revert conflicts

If the revert produces merge conflicts:

1. Resolve conflicts manually
2. Test the resolved state locally
3. Commit and push
4. Sync ArgoCD and verify

If conflicts are too complex to resolve quickly under time pressure, fall back to the emergency ArgoCD rollback and reconcile Git afterward.

## Emergency ArgoCD Rollback

Use this only when Git revert is not feasible — repository is down, you lack push access, or the situation demands immediate action (seconds, not minutes).

### View deployment history

```bash
# List deployment history
argocd app history <app-name>

# Output shows:
# ID  DATE                  REVISION
# 3   2024-01-15 10:30:00   abc1234 (main)
# 2   2024-01-14 09:00:00   def5678 (main)
# 1   2024-01-13 08:00:00   ghi9012 (main)
```

Each entry represents a previously synced state, identified by a history ID and the Git revision that was deployed.

### Perform the rollback

```bash
# Rollback to history ID 2 (the previous known-good state)
argocd app rollback <app-name> 2

# Verify the rollback
argocd app get <app-name>
```

After rollback, the application will show as **OutOfSync** because the cluster state no longer matches the current Git HEAD. This is expected and must be reconciled.

### What ArgoCD rollback actually does

1. Reads the manifests from the specified history entry
2. Applies those manifests to the cluster
3. Does NOT change Git in any way
4. The application's sync status becomes OutOfSync

The rollback state is fragile — any automated sync, self-heal, or manual sync will overwrite it with the current Git state.

## Post-Rollback Git Reconciliation

After using `argocd app rollback`, you must update Git to match the rolled-back state. Otherwise, the next sync re-applies the bad change.

### Step-by-step reconciliation

```bash
# Step 1: Disable automated sync (if enabled) to prevent re-applying bad state
argocd app set <app-name> --sync-policy none
argocd app set <app-name> --self-heal=false

# Step 2: Identify what needs to be reverted in Git
argocd app history <app-name>
# Compare the current Git HEAD with the history ID you rolled back to

# Step 3: Revert the bad commits in Git
cd <application-git-repo>
git revert <bad-commit-sha>
git push origin main

# Step 4: Sync ArgoCD to the reverted Git state
argocd app sync <app-name>

# Step 5: Verify alignment
argocd app get <app-name>
# Confirm: Sync Status = Synced (not OutOfSync)

# Step 6: Re-enable automated sync if it was previously enabled
argocd app set <app-name> --sync-policy automated
argocd app set <app-name> --self-heal
```

### Critical: Do not skip reconciliation

If you skip Git reconciliation after an ArgoCD rollback:

- The application stays OutOfSync
- Any manual sync or automated sync trigger re-deploys the bad version
- Another team member running `argocd app sync` unknowingly re-introduces the problem
- Self-heal (if enabled) automatically re-deploys the bad version

## Deployment History Management

### Inspect history details

```bash
# List recent deployments
argocd app history <app-name>

# Get details of a specific revision
argocd app get <app-name> --revision <history-id>
```

### History retention

ArgoCD retains deployment history entries based on the `spec.revisionHistoryLimit` field in the Application spec (default: 10). This means you can only roll back to one of the last 10 deployments.

```bash
# Check current history limit
argocd app get <app-name> -o json | jq '.spec.revisionHistoryLimit'
```

To increase the limit:

```bash
argocd app set <app-name> --revision-history-limit 20
```

### Comparing revisions

To understand what changed between deployments:

```bash
# Diff between current live state and a specific revision
argocd app diff <app-name> --revision <git-sha>

# View manifests at a specific revision
argocd app manifests <app-name> --revision <git-sha>
```

## Decision Flowchart

When a deployment needs to be undone:

1. **Is the Git repository accessible?**
   - Yes: Use Git revert (go to Step 2)
   - No: Use ArgoCD rollback (go to Step 4)

2. **Can you push to the target branch?**
   - Yes: `git revert <sha> && git push`
   - No: Create a revert PR and merge via the normal process

3. **Sync ArgoCD:** `argocd app sync <app-name>` and verify health.
   Done.

4. **Emergency rollback:** `argocd app rollback <app-name> <history-id>`

5. **Disable automated sync:** `argocd app set <app-name> --sync-policy none`

6. **Schedule Git reconciliation:** Create a task/ticket to revert the bad commits in Git and re-sync.

7. **After Git is reconciled:** Re-enable automated sync and verify Synced status.
