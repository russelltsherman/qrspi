# Sync Strategies Reference

Purpose: Detailed guide to ArgoCD sync modes, automation policies, sync waves, resource hooks, and safety controls for managing how applications are synchronized from Git to the cluster.

## Manual vs Automated Sync

### Manual sync (default, recommended for production)

Manual sync requires an explicit `argocd app sync` command to apply changes. ArgoCD detects drift and reports OutOfSync status, but does not act on it until told to.

```bash
# Sync an application manually
argocd app sync <app-name>

# Sync only specific resources
argocd app sync <app-name> --resource kind:Deployment:my-deploy
```

### Automated sync

Automated sync makes ArgoCD apply changes whenever it detects the live state diverges from Git. Enable it per-application:

```bash
# Enable automated sync
argocd app set <app-name> --sync-policy automated

# Disable automated sync (revert to manual)
argocd app set <app-name> --sync-policy none
```

Automated sync is appropriate for:
- Dev/staging environments where fast iteration matters
- Infrastructure components with high-confidence CI pipelines
- Applications with comprehensive automated testing before merge

Automated sync is NOT appropriate for:
- Production applications without a robust rollback strategy
- Applications where sync ordering matters (use sync waves instead)
- Multi-tenant clusters where uncoordinated syncs could cause conflicts

## Self-Heal

Self-heal detects and reverts manual changes made directly to the cluster (kubectl edits, Helm overrides, etc.). When enabled, ArgoCD re-syncs the application to match Git whenever live state diverges.

```bash
# Enable self-heal (requires automated sync)
argocd app set <app-name> --self-heal

# Disable self-heal
argocd app set <app-name> --self-heal=false
```

Self-heal only works when automated sync is enabled. It ensures Git remains the source of truth by overwriting any out-of-band changes.

**Warning:** Self-heal will revert emergency patches applied via kubectl. If you need to hotfix a production issue via kubectl, temporarily disable self-heal first:

```bash
argocd app set <app-name> --self-heal=false
# Apply emergency fix via kubectl
# Then commit the fix to Git and re-enable
argocd app set <app-name> --self-heal
```

## Auto-Prune

Auto-prune deletes Kubernetes resources that have been removed from Git. Without it, removing a manifest from Git leaves the resource running in the cluster.

```bash
# Enable auto-prune (requires automated sync)
argocd app set <app-name> --auto-prune

# Manual prune during sync
argocd app sync <app-name> --prune
```

**Safety consideration:** Auto-prune is destructive. A misplaced `git rm` or branch switch can delete running services. For production, prefer manual `--prune` during sync so you can review what will be deleted via `argocd app diff` first.

## Dry-Run Workflow

A dry-run previews what sync would change without applying anything:

```bash
# Step 1: Refresh from Git and check diff
argocd app diff <app-name> --refresh

# Step 2: Dry-run sync (server-side apply simulation)
argocd app sync <app-name> --dry-run

# Step 3: If diff looks correct, perform real sync
argocd app sync <app-name>
```

The diff command shows the difference between Git (desired) and cluster (live). The dry-run sync goes further — it simulates the server-side apply and reports any validation errors or conflicts.

## Sync Waves and Ordering

Sync waves control the order in which resources are applied during a sync. Lower wave numbers are applied first.

```yaml
# In the Kubernetes manifest metadata
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "1"
```

Wave ordering:
- Wave -1: Applied first (e.g., namespaces, CRDs)
- Wave 0: Default wave (resources without annotation)
- Wave 1: Applied after wave 0 (e.g., deployments depending on configmaps)
- Wave 2+: Applied after wave 1

Within a wave, resources are applied in a deterministic order based on kind (Namespaces before ConfigMaps before Deployments, etc.).

### Common wave patterns

```yaml
# Namespace first (wave -1)
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
  annotations:
    argocd.argoproj.io/sync-wave: "-1"

# ConfigMap/Secret before Deployment (wave 0 = default, no annotation needed)

# Deployment after its dependencies (wave 1)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  annotations:
    argocd.argoproj.io/sync-wave: "1"
```

## Resource Hooks

Resource hooks are Kubernetes Jobs or Pods that run at specific points in the sync lifecycle. They are defined using annotations on the resource.

### Hook types

| Phase | Annotation Value | When it runs |
|-------|-----------------|--------------|
| PreSync | `PreSync` | Before sync starts (e.g., database migrations) |
| Sync | `Sync` | During sync (default for all resources) |
| PostSync | `PostSync` | After all Sync resources are healthy (e.g., notifications, smoke tests) |
| SyncFail | `SyncFail` | When sync fails (e.g., alerting, cleanup) |
| Skip | `Skip` | Resource is ignored during sync |

### Hook example

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
spec:
  template:
    spec:
      containers:
      - name: migrate
        image: my-app:latest
        command: ["./migrate.sh"]
      restartPolicy: Never
```

### Hook delete policies

| Policy | Behavior |
|--------|----------|
| `HookSucceeded` | Delete hook after successful execution |
| `HookFailed` | Delete hook after failed execution |
| `BeforeHookCreation` | Delete previous hook before creating new one (default) |

Combine policies: `argocd.argoproj.io/hook-delete-policy: HookSucceeded,BeforeHookCreation`

## Force Sync

Force sync re-applies all resources, even those that are already in sync. This is useful when ArgoCD's sync state tracking has become stale.

```bash
# Force sync all resources
argocd app sync <app-name> --force

# Force sync is destructive — it deletes and recreates resources
# that cannot be patched (e.g., immutable fields on Jobs)
```

**Warning:** `--force` on resources with immutable fields (Jobs, PVCs with certain storage classes) will delete and recreate them. This causes downtime for affected workloads. Use `--force` only when regular sync fails due to immutable field conflicts.

## Apply Out-of-Sync Only

By default, sync re-applies all resources. The `apply-out-of-sync-only` optimization limits sync to only resources that differ from Git:

```bash
# Enable on an app
argocd app set <app-name> --sync-option ApplyOutOfSyncOnly=true
```

This reduces sync time and API server load for applications with many resources where only a few change per commit. It is safe to enable broadly.

## Sync Options Summary

```bash
# View current sync policy
argocd app get <app-name> -o json | jq '.spec.syncPolicy'

# Set multiple sync options
argocd app set <app-name> \
  --sync-policy automated \
  --self-heal \
  --auto-prune \
  --sync-option ApplyOutOfSyncOnly=true

# Override sync options for a single sync
argocd app sync <app-name> --prune --force
```

## Retry Policy

Configure automatic retries for failed syncs:

```bash
# Set retry policy (automated sync only)
argocd app set <app-name> \
  --sync-retry-limit 5 \
  --sync-retry-backoff-duration 5s \
  --sync-retry-backoff-factor 2 \
  --sync-retry-backoff-max-duration 3m
```

Retries are useful for transient failures (API server timeouts, temporary quota exhaustion). They are not useful for persistent errors (invalid manifests, missing CRDs).
