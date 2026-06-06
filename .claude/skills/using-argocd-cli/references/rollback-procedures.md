# Rollback Procedures

Deep reference for reverting a bad deployment in Argo CD. Loaded on demand from the
skill body's Rollbacks section.

## Opinionated default

**Prefer a Git revert over `argocd app rollback`.** Argo CD's authority is Git: a
`rollback` changes the *live* cluster to an older synced revision without changing Git,
so the desired state in Git still points at the bad version. The next automated sync (or
any teammate's manual sync) will happily re-apply the broken revision. Reverting in Git
fixes the source of truth, leaves an auditable history entry, and survives the next
reconcile. Use `app rollback` only as an emergency stopgap, and always follow it with a
Git revert.

## Emergency rollback (stopgap only)

```bash
# 1. See the deploy history and its revision IDs
argocd app history payments-prod

# 2. Roll the live cluster back to a known-good history ID
argocd app rollback payments-prod <history-id>
```

Critical side effect: **`argocd app rollback` automatically disables automated sync** on
the app. Argo CD does this on purpose — if automation stayed on, it would immediately
re-sync the app back to the (still-bad) Git HEAD and undo your rollback. The app is now
in a manual, drifted state: live = old good revision, Git = new bad revision, shown as
`OutOfSync`.

## Required follow-up: fix Git

The rollback bought you time; it did not fix the problem. Close the loop:

```bash
# Revert the offending commit(s) in the Git repo, then push
git revert <bad-sha>
git push

# Re-sync so live matches the corrected Git HEAD
argocd app sync payments-prod

# Re-enable automation if this app uses it (rollback disabled it)
argocd app set payments-prod --sync-policy automated
```

After the Git revert is merged and synced, desired (Git) and live state agree again and
the app returns to `Synced`. Leaving an app in the post-rollback drifted state is a
latent incident: the bad revision is one accidental sync away from returning.

## Inspecting history

```bash
argocd app history payments-prod              # list revisions with IDs + timestamps
argocd app get payments-prod --revision <id>  # inspect a specific revision's manifests
```

Use `app history` to identify the last healthy `history-id` before rolling back, and to
confirm which Git SHA each deployment corresponds to.
