# Rollback Procedures Reference

Detailed procedures for rolling back ArgoCD-managed applications. Git revert is the primary path; emergency rollback via ArgoCD history is the fallback.

## Rollback Philosophy

**Git revert is the primary rollback mechanism.** ArgoCD's value proposition is that Git is the source of truth. When you revert in Git and sync, the rollback is:
- **Auditable** — the revert commit shows who rolled back, when, and why
- **Reproducible** — the same Git SHA can be deployed to any cluster
- **Safe** — ArgoCD's normal diff/sync/health pipeline validates the revert

`argocd app rollback` is an emergency escape hatch. It applies a previous state from ArgoCD's internal history, creating drift between Git and the cluster. This drift must be resolved after the emergency is over.

## Primary Path: Git Revert

### Step 1: Identify the Bad Commit

```bash
# In the application's Git repository:
git log --oneline -10

# If you know the PR, use the merge commit:
git log --merges --oneline -5
```

### Step 2: Revert the Commit

```bash
# Revert a single commit
git revert <bad-commit-sha>

# Revert a merge commit (specify parent — usually -m 1 for mainline)
git revert -m 1 <merge-commit-sha>

# Push the revert
git push
```

### Step 3: Sync the Application

```bash
# ArgoCD will detect the new commit. Diff first:
argocd app diff <app-name>

# Sync to apply the revert
argocd app sync <app-name>

# Wait for healthy state
argocd app wait <app-name> --health --timeout 300
```

### Step 4: Verify

```bash
# Confirm sync status and health
argocd app get <app-name>

# Verify the deployed revision matches the revert commit
argocd app get <app-name> -o json | grep -A2 '"revision"'
```

## Emergency Rollback: ArgoCD History

Use this only when Git revert is not feasible (e.g., Git is down, the fix is complex, or immediate action is required to restore service).

### Step 1: Inspect History

```bash
# Show deployment history
argocd app history <app-name>
```

Output shows:
| Column | Meaning |
|--------|---------|
| ID | History revision number (monotonically increasing) |
| DATE | When this revision was deployed |
| REVISION | Git commit SHA that was deployed |

### Step 2: Identify the Target Revision

Pick the history ID of the last known good deployment. Verify by checking the Git SHA in the REVISION column against your repository.

### Step 3: Execute Rollback

```bash
# Rollback to a specific history ID
argocd app rollback <app-name> <history-id>

# Wait for rollback to complete
argocd app wait <app-name> --health --timeout 300
```

### Step 4: Verify

```bash
# Confirm the application is healthy
argocd app get <app-name>

# The sync status will show OutOfSync — this is expected
# because the cluster no longer matches HEAD of the Git branch
```

**The application will show OutOfSync after an emergency rollback.** This is correct — the cluster is running a previous revision while Git has moved forward. This is the drift that must be reconciled.

## Post-Rollback Git Reconciliation

After an emergency rollback, the cluster is running a different revision than Git HEAD. You must reconcile this drift.

### Option A: Revert in Git (Preferred)

```bash
# In the Git repository, revert the bad changes
git revert <bad-commit-sha>
git push

# Sync the app — it should now show Synced
argocd app sync <app-name>
argocd app get <app-name>
```

### Option B: Force Push the Rolled-Back State

Only use this if the Git history is complex and a clean revert is impractical.

```bash
# In the Git repository, reset to the rolled-back revision
git checkout <rolled-back-sha> -- <path-to-manifests>
git add .
git commit -m "Reconcile: match cluster state after emergency rollback of <bad-commit>"
git push

# Sync
argocd app sync <app-name>
```

### Option C: Disable Auto-Sync Temporarily

If auto-sync is enabled and the bad commit keeps re-syncing:

```bash
# Disable auto-sync to prevent the bad state from re-deploying
argocd app set <app-name> --sync-policy none

# Perform the emergency rollback
argocd app rollback <app-name> <history-id>

# Fix in Git (revert the bad commit)
git revert <bad-commit-sha>
git push

# Re-enable auto-sync
argocd app set <app-name> --sync-policy automated
```

## History Management

### Inspect Full History

```bash
# Show all deployment history
argocd app history <app-name>

# Show history in JSON for scripting
argocd app history <app-name> -o json
```

### History Retention

ArgoCD retains history based on the `--revision-history-limit` setting on the Application resource. The default is 10 revisions. To change it:

```bash
argocd app set <app-name> --revision-history-limit 20
```

**Do not set this too high** — each history entry stores the full rendered manifest set. High limits increase ArgoCD's memory usage.

**Do not set this to 0** — a limit of 0 means unlimited history, which can cause storage issues over time.

### Compare Revisions

```bash
# Show manifests from a specific revision in history
argocd app manifests <app-name> --revision <git-sha>

# Compare what is live vs what is in Git
argocd app manifests <app-name> --source live
argocd app manifests <app-name> --source git
```

## Rollback Decision Tree

```
Application is broken after a deployment
│
├─ Can you identify the bad Git commit?
│  ├─ Yes → Git revert → push → argocd app sync
│  └─ No  → argocd app history → find last good ID → continue below
│
├─ Is Git accessible?
│  ├─ Yes → Git revert (primary path above)
│  └─ No  → Emergency rollback below
│
├─ Is auto-sync enabled?
│  ├─ Yes → Disable auto-sync first (Option C above)
│  └─ No  → Continue
│
└─ Execute: argocd app rollback <app-name> <history-id>
   └─ After service is restored: reconcile Git (Options A or B above)
```
