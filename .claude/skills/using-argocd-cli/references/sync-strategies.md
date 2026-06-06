# Sync Strategies

Deep reference for how Argo CD reconciles desired (Git) state into a cluster, and the
flags that control it. Loaded on demand from the skill body's Sync Strategies section.

## Opinionated default

**Use manual sync for production; reserve automated sync for lower environments.**
Automated sync applies every merged change to the cluster without a human gate, which
is excellent for fast dev/stg feedback but removes the deliberate promotion step you
want in front of production. In prod, keep `syncPolicy.automated` unset and trigger
`argocd app sync` (or a promotion pipeline) explicitly, so a human or a gated job
decides when desired state reaches the cluster.

## Manual vs automated

### Manual sync

The app shows `OutOfSync` after a Git change and waits. You apply it deliberately:

```bash
argocd app diff payments-prod      # review what would change first
argocd app sync payments-prod      # apply desired state now
argocd app wait payments-prod --health   # block until healthy
```

### Automated sync

Argo CD applies changes as soon as it detects drift between Git and the cluster.

```bash
# Enable automation
argocd app set payments-stg --sync-policy automated

# Reconcile cluster drift back to Git (revert manual kubectl edits)
argocd app set payments-stg --self-heal

# Delete resources removed from Git
argocd app set payments-stg --auto-prune
```

- `--self-heal` — if someone edits a live resource out-of-band, Argo CD reverts it to
  match Git. Enforces Git as the single source of truth.
- `--auto-prune` — when a manifest is deleted from Git, the corresponding live resource
  is removed. **Off by default** because accidental deletes are destructive — enable
  consciously.

## Previewing and scoping a sync

```bash
argocd app sync payments-prod --dry-run            # server-side dry run, no changes
argocd app sync payments-prod --apply-out-of-sync-only   # only touch drifted resources
argocd app sync payments-prod --resource apps:Deployment:web   # sync one resource
```

`--apply-out-of-sync-only` reduces churn on large apps by skipping resources already in
sync rather than re-applying the whole manifest set.

## Ordering: sync waves and hooks

Control *order* within a sync using annotations on the manifests (not CLI flags):

- **Sync waves** — `argocd.argoproj.io/sync-wave: "<n>"` orders resources; lower waves
  apply first (e.g. CRDs in wave `-1`, workloads in wave `0`, smoke tests in wave `1`).
- **Hooks** — `argocd.argoproj.io/hook: PreSync|Sync|PostSync|SyncFail` run Jobs at
  defined lifecycle points (DB migration as `PreSync`, cache warm as `PostSync`).

Inspect ordering/health of an in-flight sync with `argocd app get <app>` and the
operation state.

## Force and prune cautions

```bash
argocd app sync payments-prod --prune   # delete live resources absent from Git
argocd app sync payments-prod --force   # replace via delete+recreate, not patch
```

- `--prune` deletes resources — confirm with `--dry-run` first; a stray manifest
  deletion will remove the live object.
- `--force` does `kubectl replace --force` (delete then recreate) instead of an
  in-place patch. It causes downtime and recreates the resource UID — use only to break
  out of a stuck/immutable-field state, never as a routine sync.

## Retry policy

Make automated syncs resilient to transient failures:

```bash
argocd app set payments-stg \
  --sync-retry-limit 5 \
  --sync-retry-backoff-duration 5s \
  --sync-retry-backoff-factor 2 \
  --sync-retry-backoff-max-duration 3m
```

Exponential backoff (`factor`) capped by `max-duration` avoids hammering the API on a
persistently failing sync while still recovering from blips.
