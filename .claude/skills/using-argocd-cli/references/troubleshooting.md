# Troubleshooting Reference

Diagnostic flowchart for ArgoCD application issues. Start with `argocd app get` and branch by symptom.

## Table of Contents

- [Entry Point: Get Application State](#entry-point-get-application-state)
- [Branch by Sync Status](#branch-by-sync-status) (OutOfSync, Synced but Unexpected, Unknown)
- [Branch by Health Status](#branch-by-health-status) (Degraded, Progressing, Missing, Suspended, Unknown)
- [Sync Operation Issues](#sync-operation-issues) (Stuck, Failed, Hooks Failing)
- [Cache and Refresh Issues](#cache-and-refresh-issues)
- [Application Logs](#application-logs)
- [Resource Tree](#resource-tree)
- [Quick Diagnostic Checklist](#quick-diagnostic-checklist)

## Entry Point: Get Application State

```bash
argocd app get <app-name>
```

This command is always the starting point. It shows:
- **Sync Status:** Synced, OutOfSync, Unknown
- **Health Status:** Healthy, Degraded, Progressing, Suspended, Missing, Unknown
- **Conditions:** Warnings or errors at the application level
- **Source:** Git repo, path, and target revision
- **Destination:** Cluster and namespace

## Branch by Sync Status

### OutOfSync

The cluster state does not match the Git source.

**Step 1: See what diverged**
```bash
argocd app diff <app-name>
```

**Step 2: Determine why it is out of sync**

| Observation | Likely Cause | Action |
|-------------|-------------|--------|
| Diff shows expected changes from a recent commit | Normal — changes haven't been synced yet | Sync: `argocd app sync <app-name> --dry-run` then sync |
| Diff shows changes you didn't make | Someone modified the cluster directly (kubectl edit, etc.) | Enable self-heal or sync to overwrite manual changes |
| Diff shows only metadata (labels, annotations) | Controller or operator modified the resource | Add `ignoreDifferences` to the Application spec |
| No diff output but status says OutOfSync | Cache is stale | Hard refresh: `argocd app get <app-name> --hard-refresh` |

**Step 3: If sync fails after resolving the diff**
```bash
# Check for sync errors
argocd app sync <app-name> --dry-run 2>&1

# Common error: admission webhook denied
# → Fix the manifest to comply with the webhook policy

# Common error: resource quota exceeded
# → Request quota increase or reduce resource requests
```

### Synced but Unexpected State

The sync succeeded but the application doesn't behave as expected.

```bash
# Compare rendered manifests
argocd app manifests <app-name> --source git > /tmp/git-manifests.yaml
argocd app manifests <app-name> --source live > /tmp/live-manifests.yaml
diff /tmp/git-manifests.yaml /tmp/live-manifests.yaml
```

Check for:
- Helm value overrides not applied correctly
- Kustomize patches missing
- Wrong target revision (branch vs tag vs commit)

### Unknown Sync Status

ArgoCD cannot determine the sync state.

```bash
# Force a refresh
argocd app get <app-name> --refresh

# If still Unknown, check the repo connection
argocd repo get <repo-url>

# Check for repo credential issues
argocd repo list
```

## Branch by Health Status

### Degraded

One or more resources are unhealthy.

**Step 1: Identify unhealthy resources**
```bash
argocd app resources <app-name>
```

Look for resources with health status `Degraded`. Note the resource kind and name.

**Step 2: Inspect the specific resource**
```bash
# Get resource details via ArgoCD
argocd app resources <app-name> \
  --kind <Kind> --name <resource-name> -o json

# Or use kubectl for deeper inspection
kubectl describe <kind> <resource-name> -n <namespace>
kubectl get events -n <namespace> --sort-by='.lastTimestamp'
```

**Common Degraded causes:**

| Resource | Symptom | Fix |
|----------|---------|-----|
| Deployment | Pods failing to start | Check `kubectl describe pod` for image pull errors, crash loops, resource limits |
| Service | No endpoints | Check selector labels match pod labels |
| Ingress | Health check failing | Verify backend service and readiness probe |
| PVC | Pending | Check storage class availability and quota |

### Progressing

Resources are being rolled out but haven't reached a stable state.

```bash
# Check if a rollout is in progress
kubectl rollout status deployment/<deployment-name> -n <namespace>

# Check pod status
kubectl get pods -n <namespace> -l <app-selector>
```

**If Progressing for too long (> 10 minutes):**
```bash
# Check for stuck rollout
kubectl describe deployment <deployment-name> -n <namespace>

# Look for:
# - Insufficient resources (pending pods)
# - Image pull errors
# - Readiness probe failures
# - PDB blocking rollout
```

### Missing

ArgoCD expects a resource that does not exist in the cluster.

```bash
# See what's missing
argocd app resources <app-name>
```

Causes:
- Resource was manually deleted from the cluster
- CRD is not installed (custom resources can't exist without their CRD)
- Namespace doesn't exist

Fix: Sync the application to recreate the missing resources.

### Suspended

The application or a resource is intentionally suspended.

```bash
# Check if the application has a suspended condition
argocd app get <app-name>

# Common: HPA or CronJob in suspended state — this is often intentional
```

### Unknown Health

ArgoCD doesn't know how to assess the health of a resource.

```bash
# Check the resource type
argocd app resources <app-name>
```

Custom resources may show Unknown health if ArgoCD doesn't have a health check for that CRD. This can be configured via custom health checks in `argocd-cm`.

## Sync Operation Issues

### Sync Stuck / Hanging

```bash
# Check for an ongoing sync operation
argocd app get <app-name>

# If a sync operation is stuck, terminate it
argocd app terminate-op <app-name>

# Then retry
argocd app sync <app-name>
```

### Sync Failed

```bash
# Get sync result details
argocd app get <app-name>

# Check the sync result message for the specific error
# Common errors:

# "ComparisonError" — ArgoCD can't render the manifests
# → Check Helm chart values, Kustomize config, or plain YAML syntax

# "one or more objects failed to apply" — Kubernetes rejected the manifest
# → Run dry-run to see the specific error:
argocd app sync <app-name> --dry-run

# "Resource is not permitted" — AppProject restricts this resource type
# → Add the resource type to the project's allowed resources
```

### Sync Hooks Failing

```bash
# Check hook status
argocd app resources <app-name> | grep Hook

# Get hook logs (hooks are typically Jobs)
kubectl logs job/<hook-job-name> -n <namespace>

# If PreSync hook fails, sync will not proceed
# Fix the hook, then retry sync
```

## Cache and Refresh Issues

### Stale Data

```bash
# Soft refresh — re-fetch from Git and compare
argocd app get <app-name> --refresh

# Hard refresh — clear cache and re-render manifests
argocd app get <app-name> --hard-refresh
```

**Use hard refresh when:**
- Helm dependencies changed but ArgoCD shows the old chart
- Kustomize remote bases updated but ArgoCD uses cached versions
- Repository files changed but ArgoCD diff shows no change

### Repository Connection Issues

```bash
# Test repo connectivity
argocd repo get <repo-url>

# List all configured repos
argocd repo list

# If repo shows connection error, validate credentials
argocd repo add <repo-url> --username <user> --password <token>
```

## Application Logs

```bash
# Stream logs from all pods in an application
argocd app logs <app-name> --follow

# Stream logs from a specific resource
argocd app logs <app-name> --kind Deployment --name <deployment-name>

# Show logs from a specific container
argocd app logs <app-name> --container <container-name>

# Show previous container logs (after a crash)
argocd app logs <app-name> --previous
```

## Resource Tree

```bash
# Show the full resource tree (parent-child relationships)
argocd app resource-tree <app-name>

# Useful for understanding:
# - Which Deployment owns which ReplicaSet and Pods
# - Which Service connects to which Endpoints
# - CRD → CR ownership chains
```

## Quick Diagnostic Checklist

When an application is broken and you don't know where to start:

```bash
# 1. Get the overview
argocd app get <app-name> --refresh

# 2. Check for drift
argocd app diff <app-name>

# 3. List all resources and their health
argocd app resources <app-name>

# 4. Check for stuck operations
# (look for "Operation" section in the output of step 1)

# 5. Check application events/conditions
argocd app get <app-name> -o wide

# 6. Check logs
argocd app logs <app-name> --follow

# 7. If all ArgoCD checks pass, the problem is in Kubernetes
kubectl get events -n <namespace> --sort-by='.lastTimestamp'
kubectl describe pods -n <namespace> -l <app-label>
```
