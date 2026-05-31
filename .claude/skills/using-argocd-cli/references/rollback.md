# Argo CD Rollback

Self-contained reference for rolling back an Application. Loaded from the "Rollback"
section of `SKILL.md`.

## Git revert vs `argocd app rollback`

| Approach | What it does | Source of truth after |
|----------|--------------|-----------------------|
| **Git revert (preferred)** | Revert the bad commit in the source repo, then sync. | Git — consistent, auditable. |
| `argocd app rollback` | Re-applies a previous *synced* revision from the app's history. | Diverges from Git until you reconcile. |

The default is **Git revert**. It keeps Git authoritative so the next reconcile does not
undo your fix.

```bash
# Preferred:
git revert <bad-sha> && git push
argocd app sync my-app

# Emergency only (then immediately reconcile Git to match):
argocd app history my-app
argocd app rollback my-app <history-id>
```

## History inspection

```bash
argocd app history my-app                 # list revisions: ID, revision SHA, deploy time
argocd app get my-app --revision <sha>    # inspect a specific revision's manifests
```

Identify the last-good `history-id`/SHA before rolling back. Rollback targets a history
ID, not a raw Git SHA.

## Why imperative rollback drifts

`argocd app rollback` sets the live state to an old revision, but Git still contains the
bad commit. If automated sync (or anyone's manual sync) runs, Argo CD reconciles back to
Git and re-applies the bad state. Always pair an emergency rollback with a Git revert.

## Automated rollback on degraded

Argo CD does not roll back automatically on its own. Achieve auto-rollback-on-degraded by
combining:

- A `PostSync` health-gate hook (or `argocd app wait --health`) in the pipeline, and
- Pipeline logic that, on a `Degraded` result, performs the Git revert + re-sync.

For richer progressive-delivery auto-rollback (analysis, canaries), that lives in **Argo
Rollouts**, a separate product — out of scope for this skill.
