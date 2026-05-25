# Troubleshooting Reference

Purpose: Diagnostic flowchart and targeted remediation for common ArgoCD application issues — starting from `argocd app get` output and branching by symptom to specific resolution steps.

## Table of Contents

- [Diagnostic Entry Point](#diagnostic-entry-point)
- [Symptom: OutOfSync](#symptom-outsync)
- [Symptom: Degraded Health](#symptom-degraded-health)
- [Symptom: Progressing (Stuck)](#symptom-progressing-stuck)
- [Symptom: Unknown Status](#symptom-unknown-status)
- [Symptom: Sync Failed](#symptom-sync-failed)
- [Manifest Comparison](#manifest-comparison)
- [Hard Refresh](#hard-refresh)
- [Log Streaming](#log-streaming)
- [Quick Reference: Diagnostic Commands](#quick-reference-diagnostic-commands)

## Diagnostic Entry Point

Always start troubleshooting with:

```bash
argocd app get <app-name>
```

This shows sync status, health status, and individual resource states. Branch to the appropriate section based on what you see.

## Symptom: OutOfSync

The application's desired state (Git) differs from its live state (cluster).

### Step 1: Check what is different

```bash
argocd app diff <app-name> --refresh
```

The `--refresh` flag forces ArgoCD to re-read the Git repository before comparing.

### Step 2: Branch by diff type

**Diff shows expected changes (new commit not yet synced):**
- This is normal for manual sync applications. Sync when ready:
  ```bash
  argocd app sync <app-name>
  ```

**Diff shows unexpected changes (resources modified outside Git):**
- Someone edited resources directly (kubectl, Helm, another tool)
- To restore Git as source of truth:
  ```bash
  argocd app sync <app-name>
  ```
- To prevent recurrence, enable self-heal:
  ```bash
  argocd app set <app-name> --self-heal
  ```

**Diff shows resources that should not exist:**
- Resources were removed from Git but not pruned from the cluster
- Sync with prune:
  ```bash
  argocd app diff <app-name>  # Review what will be deleted
  argocd app sync <app-name> --prune
  ```

**No diff but still OutOfSync:**
- ArgoCD's cache may be stale. Hard-refresh:
  ```bash
  argocd app get <app-name> --hard-refresh
  ```

## Symptom: Degraded Health

One or more application resources are in a failed or error state.

### Step 1: Identify unhealthy resources

```bash
argocd app get <app-name> -o json | jq '.status.resources[] | select(.health.status != "Healthy")'
```

### Step 2: Inspect the resource

```bash
# View resource details
argocd app resources <app-name> --kind <Kind> --name <resource-name>

# View events for the resource
kubectl describe <kind> <resource-name> -n <namespace>

# View pod logs (for Deployment/Pod issues)
argocd app logs <app-name> --kind Deployment --name <deployment-name>
```

### Step 3: Branch by resource type

**Deployment — pods not starting:**
```bash
# Check pod status
kubectl get pods -n <namespace> -l app=<app-label>

# Check events for crash reasons
kubectl describe pod <pod-name> -n <namespace>

# Check container logs
argocd app logs <app-name> --kind Deployment --name <deploy-name> --follow
```

Common causes:
- Image pull errors (wrong image tag, registry auth)
- CrashLoopBackOff (application error, missing config)
- Resource limits (OOMKilled, CPU throttling)

**Service — endpoints not ready:**
```bash
kubectl get endpoints <service-name> -n <namespace>
```

Usually means the selector does not match any running pods.

**PersistentVolumeClaim — pending:**
```bash
kubectl describe pvc <pvc-name> -n <namespace>
```

Usually means no StorageClass or insufficient capacity.

## Symptom: Progressing (Stuck)

The application has been in "Progressing" state for longer than expected.

### Step 1: Check what is progressing

```bash
argocd app get <app-name> -o json | jq '.status.resources[] | select(.health.status == "Progressing")'
```

### Step 2: Check for stuck operations

```bash
# Check if a sync operation is in progress
argocd app get <app-name> -o json | jq '.status.operationState'
```

If an operation is stuck:
```bash
# Terminate the stuck operation
argocd app terminate-op <app-name>

# Then investigate why it stalled
argocd app get <app-name>
```

### Step 3: Common causes of stuck progress

**Deployment rollout not completing:**
```bash
kubectl rollout status deployment/<name> -n <namespace>
```

- New pods failing to become ready (readiness probe failing)
- Old pods not terminating (PDB blocking, finalizers)
- Insufficient cluster resources to schedule new pods

**Hook job not completing:**
```bash
kubectl get jobs -n <namespace> -l argocd.argoproj.io/hook
kubectl logs job/<hook-job-name> -n <namespace>
```

- PreSync hook (e.g., database migration) is failing or taking too long
- PostSync hook waiting for a condition that will never be met

## Symptom: Unknown Status

ArgoCD cannot determine the health or sync status of the application.

### Step 1: Check connectivity

```bash
# Verify the target cluster is reachable
argocd cluster list
argocd cluster get <cluster-url>
```

### Step 2: Check repository access

```bash
# Verify repository is accessible
argocd repo list
argocd repo get <repo-url>
```

If the repository shows errors:
```bash
# Test repository connectivity
argocd repo add <repo-url> --username <user> --password <token>
```

### Step 3: Force refresh

```bash
argocd app get <app-name> --hard-refresh
```

Hard-refresh clears all caches and re-reads from both Git and the cluster.

## Symptom: Sync Failed

The sync operation started but failed to complete.

### Step 1: Check the operation result

```bash
argocd app get <app-name> -o json | jq '.status.operationState'
```

This shows the sync result, message, and which phase failed.

### Step 2: Branch by failure type

**Manifest validation error:**
```bash
# Dry-run to see the validation error
argocd app sync <app-name> --dry-run
```

Common causes:
- Invalid YAML/JSON in manifests
- Schema validation failure (wrong API version, missing required fields)
- Immutable field change (e.g., changing a Job's spec)

For immutable field errors, you may need force sync:
```bash
argocd app sync <app-name> --force
```

**Warning:** Force sync deletes and recreates the resource. This causes downtime.

**Permission error:**
- The ArgoCD service account lacks permissions to create/update the resource
- Check the ArgoCD controller logs:
  ```bash
  kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller --tail=100
  ```

**Resource hook failure:**
```bash
# Check hook job logs
kubectl get jobs -n <namespace> -l argocd.argoproj.io/hook
kubectl logs job/<failed-hook-job> -n <namespace>
```

**Timeout:**
- The sync took longer than the configured timeout
- Retry with a longer timeout:
  ```bash
  argocd app sync <app-name> --timeout 600
  ```

## Manifest Comparison

Compare what ArgoCD thinks should be deployed versus what is in the cluster:

```bash
# Show desired (Git) manifests
argocd app manifests <app-name> --source git

# Show live (cluster) manifests
argocd app manifests <app-name> --source live

# Side-by-side diff
argocd app diff <app-name>
```

If the diff shows unexpected differences in computed fields (e.g., labels added by admission controllers), configure ArgoCD to ignore those paths in the Application spec:

```yaml
spec:
  ignoreDifferences:
  - group: apps
    kind: Deployment
    jsonPointers:
    - /spec/template/metadata/annotations/kubectl.kubernetes.io~1last-applied-configuration
```

## Hard Refresh

When ArgoCD's cached state seems wrong, force a complete re-read:

```bash
# Hard-refresh: re-read from both Git and cluster
argocd app get <app-name> --hard-refresh

# If hard-refresh does not resolve stale cache:
# 1. Check if the ArgoCD repo-server is healthy
kubectl get pods -n argocd -l app.kubernetes.io/name=argocd-repo-server

# 2. Check repo-server logs for errors
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-repo-server --tail=50

# 3. As a last resort, restart the repo-server
kubectl rollout restart deployment/argocd-repo-server -n argocd
```

## Log Streaming

For real-time debugging of application issues:

```bash
# Stream logs from all containers in an application
argocd app logs <app-name> --follow

# Stream logs from a specific resource
argocd app logs <app-name> --kind Deployment --name <name> --follow

# Stream logs from a specific container
argocd app logs <app-name> --kind Deployment --name <name> \
  --container <container-name> --follow

# View previous container logs (after crash)
argocd app logs <app-name> --kind Deployment --name <name> --previous
```

## Quick Reference: Diagnostic Commands

| Symptom | First Command | Next Step |
|---------|--------------|-----------|
| OutOfSync | `argocd app diff <app> --refresh` | Review diff, sync or hard-refresh |
| Degraded | `argocd app get <app> -o json \| jq '.status.resources[]'` | Inspect unhealthy resources |
| Progressing | `argocd app get <app> -o json \| jq '.status.operationState'` | Terminate-op if stuck |
| Unknown | `argocd cluster list` | Check connectivity |
| Sync Failed | `argocd app sync <app> --dry-run` | Identify validation errors |
| Stale State | `argocd app get <app> --hard-refresh` | Clear all caches |
