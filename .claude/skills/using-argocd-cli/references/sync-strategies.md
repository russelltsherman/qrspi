# Sync Strategies Reference

Detailed guide to ArgoCD sync policies, automated sync behavior, sync waves, resource hooks, and safe sync practices.

## Manual Sync (Default)

Manual sync requires explicit `argocd app sync` invocation. This is the recommended default for production because it preserves human review.

```bash
# Sync an application
argocd app sync <app-name>

# Sync specific resources only
argocd app sync <app-name> --resource <group>:<kind>:<name>

# Sync and prune orphaned resources
argocd app sync <app-name> --prune

# Sync only out-of-sync resources (faster for large apps)
argocd app sync <app-name> --apply-out-of-sync-only
```

## Dry-Run Workflow

Always dry-run before syncing in production. A dry-run validates the manifests against the Kubernetes API server (admission controllers, schema validation, resource quotas) without applying changes.

```bash
# Step 1: Diff — see what will change
argocd app diff <app-name>

# Step 2: Dry-run — validate against API server
argocd app sync <app-name> --dry-run

# Step 3: Sync — apply for real (only after reviewing dry-run output)
argocd app sync <app-name> --prune
```

**Why both diff and dry-run?** Diff compares Git manifests to live state (catches drift). Dry-run submits to the API server without applying (catches admission webhook rejections, quota violations, schema errors). They test different failure modes.

## Automated Sync

Automated sync makes ArgoCD apply changes automatically when Git changes are detected. Configure it via the application's sync policy:

```bash
# Enable automated sync
argocd app set <app-name> --sync-policy automated

# Enable automated sync with auto-prune
argocd app set <app-name> --sync-policy automated --auto-prune

# Enable automated sync with self-heal
argocd app set <app-name> --sync-policy automated --self-heal
```

### Auto-Prune

When enabled, resources deleted from Git are automatically deleted from the cluster during sync.

**Without auto-prune:** Deleted resources become orphans — they remain in the cluster but are no longer tracked by ArgoCD. You must manually delete them.

**With auto-prune:** The cluster state matches Git exactly. This is correct for most environments, but dangerous if someone accidentally deletes a manifest from Git.

```bash
# Enable auto-prune
argocd app set <app-name> --auto-prune

# Disable auto-prune
argocd app set <app-name> --auto-prune=false
```

### Self-Heal

When enabled, ArgoCD reverts manual changes made directly to the cluster (e.g., via `kubectl edit`). It continuously compares live state to Git and resyncs when drift is detected.

**Use self-heal for:** Environments where manual cluster modifications are prohibited (production, compliance-regulated clusters).

**Avoid self-heal for:** Development environments where developers need to experiment with live changes.

```bash
# Enable self-heal
argocd app set <app-name> --self-heal

# Disable self-heal
argocd app set <app-name> --self-heal=false
```

## Sync Waves

Sync waves control the order in which resources are applied. Resources with lower wave numbers are synced first. Use waves when resources have dependencies (e.g., CRDs before custom resources, namespaces before deployments).

Annotate resources in your manifests:
```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "0"   # Applied first
---
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "1"   # Applied second
```

ArgoCD processes waves sequentially:
1. All wave-0 resources are applied and must become healthy
2. Then wave-1 resources are applied
3. And so on

**Common wave ordering:**
| Wave | Resource Type |
|------|--------------|
| -1 | Namespaces, CRDs |
| 0 | ConfigMaps, Secrets, ServiceAccounts |
| 1 | Deployments, StatefulSets, Services |
| 2 | Ingresses, NetworkPolicies |
| 3 | Jobs, CronJobs (post-deploy tasks) |

## Resource Hooks

Hooks run Jobs or other resources at specific points in the sync lifecycle. They are defined by annotations on resources in your Git manifests.

### Hook Types

| Hook | When it runs | Use case |
|------|-------------|----------|
| `PreSync` | Before any resources are synced | Database migrations, schema changes |
| `Sync` | During sync (same as normal resources) | Rarely used explicitly |
| `PostSync` | After all resources are synced and healthy | Smoke tests, notifications, cache warming |
| `SyncFail` | When sync fails | Alert notifications, cleanup |
| `Skip` | Never synced (managed externally) | Resources created by operators |

### Hook Annotations

```yaml
metadata:
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
```

### Hook Delete Policies

| Policy | Behavior |
|--------|----------|
| `HookSucceeded` | Delete the hook resource after it succeeds |
| `HookFailed` | Delete the hook resource after it fails |
| `BeforeHookCreation` | Delete previous hook before creating the new one (default) |

## Force Sync

Force sync re-applies all resources regardless of whether they are in sync. Use it when the application state is corrupted or when ArgoCD's cache is stale.

```bash
# Force sync — re-applies everything
argocd app sync <app-name> --force

# Force sync with replace instead of apply
argocd app sync <app-name> --force --replace
```

**Caution with `--force`:**
- It bypasses the diff check — resources are applied even if they appear in sync
- Combined with `--replace`, it deletes and re-creates resources (causes downtime for non-replicated workloads)
- Use only as a last resort when standard sync fails

**Caution with `--replace`:**
- Uses `kubectl replace` instead of `kubectl apply`
- Deletes and re-creates the resource, which causes brief unavailability
- Resets any fields not in the Git manifest (including runtime-added fields)
- Never use on StatefulSets with persistent volumes without understanding the implications

## Selective Sync

Sync specific resources instead of the entire application:

```bash
# Sync a specific deployment
argocd app sync <app-name> --resource apps:Deployment:my-deployment

# Sync all resources of a kind
argocd app sync <app-name> --resource :Service:

# Sync multiple specific resources
argocd app sync <app-name> \
  --resource apps:Deployment:frontend \
  --resource :Service:frontend-svc
```

## Retry Policy

Configure automatic retry for failed syncs:

```bash
# Set retry with backoff
argocd app set <app-name> \
  --sync-retry-limit 5 \
  --sync-retry-backoff-duration 5s \
  --sync-retry-backoff-factor 2 \
  --sync-retry-backoff-max-duration 3m
```

This is useful for transient failures (API server timeouts, webhook delays). Do not use high retry limits for persistent errors — they mask the root cause.

## Sync Windows

Sync windows restrict when syncing is allowed. They are configured on AppProjects, not individual applications.

```bash
# Add a sync window to a project (allow sync only during maintenance)
argocd proj windows add <project-name> \
  --kind allow \
  --schedule "0 2 * * 6" \
  --duration 4h \
  --applications "*"

# Add a deny window (block sync during business hours)
argocd proj windows add <project-name> \
  --kind deny \
  --schedule "0 9 * * 1-5" \
  --duration 8h \
  --applications "*"

# List sync windows
argocd proj windows list <project-name>
```

**Sync window behavior:**
- If only `allow` windows exist: sync is blocked outside those windows
- If only `deny` windows exist: sync is allowed except during those windows
- If both exist: sync is allowed only when an `allow` window is active AND no `deny` window is active
- Manual sync by admins can override sync windows with the `--force` flag
