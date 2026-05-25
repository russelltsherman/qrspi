---
name: using-argocd-cli
description: "Use for ANY request involving ArgoCD application management via the argocd CLI — syncing apps, checking health, diffing manifests, rolling back deployments, managing ApplicationSets, configuring RBAC/AppProjects, or troubleshooting sync failures. Trigger on: argocd commands, ArgoCD application lifecycle operations, GitOps sync workflows, ArgoCD rollback, ArgoCD app creation, ArgoCD health checks, ArgoCD diff, ArgoCD project configuration. Do NOT trigger for: kubectl commands, helm install/upgrade, flux operations, ArgoCD server installation, or general Kubernetes manifest authoring."
command: using-argocd-cli
argument-hint: <argocd-operation-or-question>
---

# ArgoCD CLI Skill

Opinionated guide for managing ArgoCD applications via the `argocd` CLI. Covers the full application lifecycle with defaults tuned for production safety.

## Prerequisites

Before any ArgoCD CLI operation:

1. **Verify CLI is installed:**
   ```bash
   argocd version --client
   ```
2. **Verify server connectivity:**
   ```bash
   argocd cluster list
   ```
   If this fails, authenticate first — see the authentication reference below.

3. **Confirm the target context:**
   ```bash
   argocd context
   ```
   Verify you are pointed at the correct ArgoCD server before mutating state.

## Authentication Overview

**Default: token-based auth.** Token auth is stateless, auditable, and works in both interactive and CI/CD contexts. Avoid password-based login for production workflows — it creates session state that expires unpredictably.

**Interactive quick start:**
```bash
# Login to ArgoCD server (creates a local session token)
argocd login <server-address> --grpc-web

# Verify authentication
argocd account get-user-info
```

**CI/CD quick start:**
```bash
# Use ARGOCD_AUTH_TOKEN environment variable (no login needed)
export ARGOCD_AUTH_TOKEN="<project-scoped-token>"
argocd app list --server <server-address> --grpc-web
```

> When the user needs detailed authentication patterns (token generation, context management, core mode, project-scoped tokens, admin password rotation), read `references/authentication.md`.

## Core Application Lifecycle

The standard lifecycle follows this sequence. Each step builds on the previous one — do not skip steps in production.

### 1. Create an Application

```bash
argocd app create <app-name> \
  --repo <git-repo-url> \
  --path <manifests-path> \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace <namespace> \
  --project <project-name> \
  --sync-policy none
```

**Why `--sync-policy none`:** Default to manual sync for production applications. Automated sync removes the human review checkpoint before changes reach a cluster. Use automated sync only for non-production environments where fast feedback outweighs safety. See the sync strategies reference for automated sync configuration.

### 2. Get Application Status

```bash
# Summary view
argocd app get <app-name>

# Watch health and sync status in real time
argocd app get <app-name> --refresh
```

The output shows: sync status (Synced/OutOfSync), health status (Healthy/Degraded/Progressing/Missing), and the source revision. This is your primary diagnostic entry point.

### 3. Diff Before Sync

**Always diff before syncing.** This is non-negotiable for production.

```bash
# Show what would change
argocd app diff <app-name>

# Exit code: 0 = no diff, 1 = differences exist
echo $?
```

Review the diff output carefully. If the diff shows unexpected changes, investigate before proceeding.

### 4. Sync (Deploy)

```bash
# Dry-run first — see what Kubernetes would do without applying
argocd app sync <app-name> --dry-run

# If dry-run looks correct, sync for real
argocd app sync <app-name> --prune
```

**Why dry-run first:** A dry-run validates against the Kubernetes API server (admission controllers, schema validation) without mutating state. It catches errors that `argocd app diff` cannot detect.

**Why `--prune`:** Without `--prune`, resources deleted from Git remain in the cluster as orphans. Include `--prune` to match the cluster state to Git. If you are uncertain about pruning, omit it on the first sync and review orphaned resources manually.

### 5. Monitor Sync Progress

```bash
# Wait for sync to complete (useful in CI/CD)
argocd app wait <app-name> --timeout 300

# Stream application events
argocd app get <app-name> --refresh -o wide
```

The `wait` command blocks until the application reaches a terminal state (Synced + Healthy, or error). Use the `--timeout` flag to prevent indefinite hangs in CI/CD pipelines.

### 6. Rollback

**Default: revert in Git, then sync.** Git revert preserves history, maintains the Git-as-source-of-truth principle, and ensures the rollback is auditable.

```bash
# In your Git repository:
git revert <bad-commit-sha>
git push

# Then sync the ArgoCD application to pick up the revert
argocd app sync <app-name>
```

**Emergency rollback** (when Git revert is too slow or blocked):
```bash
# Check deployment history
argocd app history <app-name>

# Rollback to a specific revision
argocd app rollback <app-name> <history-id>
```

After an emergency rollback, always reconcile Git to match the rolled-back state. An emergency rollback creates drift between Git and the cluster — this must be resolved.

> When the user needs detailed rollback procedures, post-rollback reconciliation steps, or history inspection, read `references/rollback-procedures.md`.

### 7. Delete an Application

```bash
# Delete the ArgoCD application AND its Kubernetes resources
argocd app delete <app-name> --cascade

# Delete the ArgoCD application but KEEP Kubernetes resources
argocd app delete <app-name> --cascade=false
```

**Default to `--cascade`** unless you are migrating the application to a different management system. With `--cascade=false`, the resources become unmanaged — they stay in the cluster but ArgoCD stops tracking them.

## Opinionated Defaults Summary

| Default | Reasoning |
|---------|-----------|
| Manual sync for production | Preserves human review before changes reach production clusters |
| Git revert over `argocd app rollback` | Maintains Git as single source of truth; rollback is auditable and reproducible |
| Token auth over password auth | Stateless, auditable, works consistently in interactive and CI/CD contexts |
| Dry-run before every sync | Catches API server validation errors before they affect the cluster |
| `--prune` on sync | Prevents orphaned resources from accumulating; matches cluster to Git |
| `--grpc-web` on login | Works through HTTP proxies and load balancers that strip HTTP/2 |

## Interactive Workflow

The interactive workflow is the default context. When working interactively:

1. **Explore first:** Use `argocd app list` and `argocd app get` to understand current state.
2. **Diff before acting:** Always run `argocd app diff` before `argocd app sync`.
3. **Use `--refresh`:** Force a live comparison with the cluster, not a cached state.
4. **Stream logs for debugging:**
   ```bash
   argocd app logs <app-name> --follow
   ```
5. **Inspect individual resources:**
   ```bash
   argocd app resources <app-name>
   argocd app resource-tree <app-name>
   ```

## CI/CD Delta

In CI/CD pipelines, adjust the interactive defaults as follows:

| Aspect | Interactive | CI/CD |
|--------|-------------|-------|
| Authentication | `argocd login` (session token) | `ARGOCD_AUTH_TOKEN` env var (no login step) |
| Server flag | Omitted (uses current context) | `--server <addr>` on every command |
| gRPC transport | `--grpc-web` if behind proxy | `--grpc-web` always (assume proxy) |
| Core mode | Not used | `--core` if running inside the cluster |
| Sync wait | Watch output visually | `argocd app wait --timeout <seconds>` |
| Auth scope | User account | Project-scoped role token (least privilege) |

**CI/CD sync pattern:**
```bash
export ARGOCD_AUTH_TOKEN="${ARGOCD_TOKEN}"

# Sync and wait for health
argocd app sync <app-name> \
  --server <server-address> \
  --grpc-web \
  --prune \
  --timeout 300

# Explicit wait with health check
argocd app wait <app-name> \
  --server <server-address> \
  --grpc-web \
  --health \
  --timeout 300
```

> When the user is configuring CI/CD authentication (project-scoped tokens, core mode, headless auth), read `references/authentication.md`.

## Escalation Path

Start simple and escalate only when complexity demands it:

### Level 1: Single Application
Manage one application with `argocd app create/sync/delete`. This covers most use cases and should be the starting point for any new deployment. Use the core lifecycle above.

**Signs you should stay at Level 1:**
- Fewer than 5 applications
- Single cluster
- Each application has unique configuration

### Level 2: App-of-Apps Pattern
When managing 5-20 related applications, use the app-of-apps pattern — a parent ArgoCD Application whose source repository contains child Application manifests. The parent syncs the children automatically.

**Signs you need Level 2:**
- 5-20 applications with related lifecycle
- Want a single Git commit to deploy multiple apps together
- Need to version application sets as a unit

```bash
# Create a parent application that manages child apps
argocd app create apps-root \
  --repo <git-repo-url> \
  --path apps/ \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace argocd
```

### Level 3: ApplicationSets
When managing more than 20 applications or deploying across more than 3 clusters, transition to ApplicationSets. ApplicationSets use generators (Git, Cluster, Matrix, List) to template Application resources programmatically.

**Signs you need Level 3:**
- More than 20 applications following a repeatable pattern
- Deploying the same app across more than 3 clusters
- App-of-apps YAML files have become copy-paste boilerplate

```bash
# List ApplicationSets
argocd appset list

# Get details of an ApplicationSet
argocd appset get <appset-name>
```

> When the user needs ApplicationSet generator types, production safety settings, or transition criteria, read `references/applicationsets.md`.

### Level 4: Multi-Cluster
For multi-cluster deployments, register additional clusters and use ApplicationSet cluster generators to target them:

```bash
# Register a cluster with ArgoCD
argocd cluster add <context-name>

# List registered clusters
argocd cluster list

# Get cluster details
argocd cluster get <cluster-server-url>
```

**Signs you need Level 4:**
- Applications must run in multiple Kubernetes clusters (DR, regional, multi-cloud)
- Different clusters have different RBAC or network policies
- Need cluster-level isolation between teams or environments

> When the user needs RBAC isolation between clusters or projects, read `references/rbac-configuration.md`.

## Sync Strategies Reference

ArgoCD supports manual sync, automated sync, self-heal, and auto-prune. The choice affects how quickly changes propagate and how much human oversight is preserved.

> When the user asks about sync strategies, automated sync policies, sync waves, resource hooks, or force sync safety, read `references/sync-strategies.md`.

## RBAC and Project Isolation

ArgoCD uses AppProjects to isolate applications by team, environment, or security boundary. Projects control which repositories, clusters, and namespaces an application can target.

```bash
# List projects
argocd proj list

# Get project details
argocd proj get <project-name>

# Create a project with restricted destinations
argocd proj create <project-name> \
  --dest <cluster>,<namespace> \
  --src <repo-url>
```

> When the user needs project-scoped roles, JWT tokens, deny-all policies, or production sync restrictions, read `references/rbac-configuration.md`.

## Troubleshooting Quick Start

When an application is unhealthy or out of sync:

1. **Start with `argocd app get <app-name>`** — this shows sync status, health, and conditions.
2. **If OutOfSync:** Run `argocd app diff <app-name>` to see what diverged.
3. **If Degraded/Progressing:** Check resource-level health:
   ```bash
   argocd app resources <app-name>
   ```
4. **If sync is stuck:** Check for ongoing operations:
   ```bash
   argocd app terminate-op <app-name>
   ```
5. **If manifests look wrong:** Compare rendered manifests:
   ```bash
   argocd app manifests <app-name> --source live
   argocd app manifests <app-name> --source git
   ```
6. **If cache is stale:** Force a hard refresh:
   ```bash
   argocd app get <app-name> --hard-refresh
   ```

> When the user needs the full diagnostic flowchart with branching logic by symptom, read `references/troubleshooting.md`.

## Common Operations Quick Reference

```bash
# List all applications
argocd app list

# List applications in a specific project
argocd app list --project <project-name>

# Get application details in JSON (for scripting)
argocd app get <app-name> -o json

# Patch application settings
argocd app set <app-name> --revision <branch-or-tag>
argocd app set <app-name> --values-file values-prod.yaml

# Run a resource action (e.g., restart a Deployment)
argocd app actions run <app-name> restart --kind Deployment --resource-name <name>

# List available actions for an application's resources
argocd app actions list <app-name>
```

## Reference Files

This skill includes six reference files for deep-dive topics. Load them on demand based on the user's specific need:

| File | Load when... |
|------|-------------|
| `references/authentication.md` | User needs token generation, context management, core mode, project-scoped tokens, or admin password rotation |
| `references/sync-strategies.md` | User asks about automated sync, self-heal, auto-prune, sync waves, resource hooks, or force sync |
| `references/rollback-procedures.md` | User needs rollback steps, post-rollback Git reconciliation, or deployment history inspection |
| `references/applicationsets.md` | User needs ApplicationSet generators, production safety settings, or app-of-apps transition guidance |
| `references/rbac-configuration.md` | User needs AppProject isolation, project-scoped roles, JWT tokens, or production sync restrictions |
| `references/troubleshooting.md` | User needs the full diagnostic flowchart or is debugging a specific sync/health failure |

Do not load all reference files at once. Read only the file matching the user's current question.
