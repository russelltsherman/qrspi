---
name: using-argocd-cli
description: "Use for ANY request involving ArgoCD CLI operations — application management, sync, rollback, diff, health checks, or GitOps workflows. Trigger when the user wants to: create or delete ArgoCD applications, sync or diff application state, check application health or status, perform rollbacks or deployment history inspection, manage ArgoCD projects or RBAC, configure ApplicationSets or app-of-apps patterns, troubleshoot out-of-sync or degraded applications, set up ArgoCD authentication or contexts, or run any argocd CLI command. This skill covers interactive developer use and CI/CD pipeline automation. Do NOT trigger for: kubectl commands without ArgoCD context, Helm chart authoring, Flux CD operations, or ArgoCD server installation/upgrade."
command: using-argocd-cli
argument-hint: <argocd-operation or question>
---

# ArgoCD CLI Skill

Guide for managing applications, deployments, and GitOps workflows using the `argocd` CLI. Covers the full application lifecycle from creation through monitoring, rollback, and deletion.

## Prerequisites

Before running any `argocd` command, verify:

1. **CLI installed:** `argocd version --client` must succeed
2. **Server reachable:** the target ArgoCD server must be running and network-accessible
3. **Authenticated:** either logged in via `argocd login` or using a token via `ARGOCD_AUTH_TOKEN`

If authentication is not established, set it up first — see the [Authentication Reference](#reference-authentication) section.

## Opinionated Defaults

These defaults apply unless the user explicitly requests otherwise. Each includes reasoning so you can apply judgment when context warrants deviation.

### Manual sync for production

**Default:** Always use manual sync (`argocd app sync <app>`) for production applications. Do not enable automated sync on production apps.

**Reasoning:** Automated sync removes the human gate before production changes. A bad commit auto-deploying to production is harder to catch than a bad commit waiting for manual sync. For non-production environments, automated sync is acceptable and often preferred for fast iteration.

### Git revert over argocd rollback

**Default:** When the user needs to undo a deployment, prefer `git revert` of the offending commit over `argocd app rollback`.

**Reasoning:** `argocd app rollback` restores the previous Kubernetes state but does not update Git. This creates drift between Git (source of truth) and the cluster. On the next sync, ArgoCD will re-apply the bad state from Git. A Git revert keeps Git and the cluster aligned. Use `argocd app rollback` only as an emergency measure when Git operations are blocked, and always reconcile Git afterward. See [Rollback Reference](#reference-rollback-procedures) for the full procedure.

### Token-based authentication

**Default:** Use token-based auth (`ARGOCD_AUTH_TOKEN`) over interactive login for any automated or scripted context.

**Reasoning:** Interactive login (`argocd login`) creates a session that expires. Token auth is stateless, auditable, and scoped to a project. For interactive developer sessions, `argocd login` is fine. See [Authentication Reference](#reference-authentication) for token setup.

### Dry-run before sync

**Default:** Run `argocd app diff <app>` before every `argocd app sync` to preview changes.

**Reasoning:** Sync is a destructive operation that modifies cluster state. Reviewing the diff first catches unexpected changes — wrong branch, unintended resource deletions, or config drift. This is especially important when syncing with `--prune`, which deletes resources removed from Git.

## Core Application Lifecycle

This is the standard workflow for managing an ArgoCD application. Steps are presented in lifecycle order.

### Create an application

```bash
# From a Git repository
argocd app create <app-name> \
  --repo <git-repo-url> \
  --path <manifests-path> \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace <namespace> \
  --project <project-name>

# From a Helm chart
argocd app create <app-name> \
  --repo <helm-repo-url> \
  --helm-chart <chart-name> \
  --revision <chart-version> \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace <namespace>
```

Use `--project` to assign the app to an AppProject for RBAC isolation. If omitted, the app goes into the `default` project.

### Get application status

```bash
# Summary view
argocd app get <app-name>

# Specific output fields
argocd app get <app-name> -o json | jq '.status.sync.status'
argocd app get <app-name> -o json | jq '.status.health.status'
```

The output shows sync status (Synced/OutOfSync), health status (Healthy/Degraded/Progressing/Missing), and individual resource states. This is the starting point for any troubleshooting — see [Troubleshooting Reference](#reference-troubleshooting).

### Diff before sync

```bash
# Show what would change on sync
argocd app diff <app-name>

# Exit code: 0 = no diff, 1 = diff exists, 2 = error
argocd app diff <app-name> --refresh
```

Always run diff before sync. The `--refresh` flag forces ArgoCD to re-read from Git before comparing.

### Sync an application

```bash
# Basic sync
argocd app sync <app-name>

# Sync specific resources only
argocd app sync <app-name> --resource kind:Deployment:name

# Sync with prune (delete resources removed from Git)
argocd app sync <app-name> --prune

# Dry-run sync (preview only, no changes applied)
argocd app sync <app-name> --dry-run
```

For production, always diff first, then sync without `--prune` unless explicitly intended. See [Sync Strategies Reference](#reference-sync-strategies) for advanced options including sync waves, hooks, and automated sync configuration.

### Monitor sync progress

```bash
# Wait for sync to complete (useful in CI/CD)
argocd app wait <app-name> --timeout 300

# Watch health status in real time
argocd app wait <app-name> --health --timeout 300
```

In CI/CD pipelines, always use `argocd app wait` with a `--timeout` to fail the pipeline if sync takes too long. Do not poll with `argocd app get` in a loop.

### Rollback a deployment

**Preferred approach — Git revert:**

```bash
# In the application's Git repository
git revert <bad-commit-sha>
git push origin main

# Then sync ArgoCD to pick up the revert
argocd app sync <app-name>
```

**Emergency approach — ArgoCD rollback:**

```bash
# View deployment history
argocd app history <app-name>

# Rollback to a specific revision
argocd app rollback <app-name> <history-id>
```

After using `argocd app rollback`, you must reconcile Git — otherwise the next sync will re-apply the bad state. See [Rollback Reference](#reference-rollback-procedures) for the full procedure including post-rollback Git reconciliation.

### Delete an application

```bash
# Delete app and its Kubernetes resources (cascade)
argocd app delete <app-name>

# Delete app record only, leave Kubernetes resources running
argocd app delete <app-name> --cascade=false
```

Use `--cascade=false` when transferring ownership of resources to another management tool or when you want to remove ArgoCD tracking without affecting the running workload.

### List applications

```bash
# All applications
argocd app list

# Filter by project
argocd app list --project <project-name>

# Filter by sync status
argocd app list -o json | jq '.[] | select(.status.sync.status == "OutOfSync")'
```

## Interactive Workflow (Default)

The default context is interactive developer use at a terminal. This assumes:

- You have logged in via `argocd login <server>`
- You are working with a single cluster
- You want to see output and make decisions before proceeding

Standard interactive flow:

1. `argocd app get <app>` — check current state
2. `argocd app diff <app>` — preview pending changes
3. `argocd app sync <app>` — apply changes (after reviewing diff)
4. `argocd app get <app>` — verify result

## CI/CD Pipeline Context

In CI/CD, the following deltas apply from the interactive default:

- **Authentication:** Use `ARGOCD_AUTH_TOKEN` environment variable instead of `argocd login`. The token should be a project-scoped role token, not an admin token. See [Authentication Reference](#reference-authentication) for token creation.

- **Server connection:** Set `ARGOCD_SERVER` environment variable. Add `--grpc-web` if the pipeline cannot use gRPC (common behind HTTP load balancers). Add `--insecure` only if TLS is terminated upstream (not recommended in production).

- **Non-interactive mode:** ArgoCD CLI commands are non-interactive by default when stdin is not a TTY, which is the case in most CI runners.

- **Wait with timeout:** Always use `argocd app wait <app> --timeout <seconds>` after sync. Set the timeout to match your pipeline's tolerance. A missing timeout can hang the pipeline indefinitely.

- **Core mode:** If the CI runner has direct Kubernetes API access to the cluster running ArgoCD, use `--core` flag to bypass the ArgoCD API server entirely. This eliminates the need for `ARGOCD_SERVER` and `ARGOCD_AUTH_TOKEN`. See [Authentication Reference](#reference-authentication) for core mode details.

```bash
# Typical CI/CD sync pattern
export ARGOCD_AUTH_TOKEN="$ARGOCD_TOKEN"
export ARGOCD_SERVER="argocd.example.com"

argocd app diff "$APP_NAME" --grpc-web --refresh
argocd app sync "$APP_NAME" --grpc-web --prune --timeout 300
argocd app wait "$APP_NAME" --grpc-web --health --timeout 300
```

## Escalation Path

Start simple. Escalate only when complexity demands it.

### Single application

Manage one application with `argocd app create/sync/delete`. This is the right level for most use cases — a single service backed by a single Git path.

### App-of-apps pattern

When you have 5-20 related applications, create a parent application whose Git path contains Application manifests for each child. The parent syncs to create/update the children. Use this when applications share a deployment lifecycle but have separate manifests.

```bash
# The parent app points to a directory of Application CRDs
argocd app create platform-apps \
  --repo https://github.com/org/platform.git \
  --path apps/ \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace argocd
```

### ApplicationSets

When you exceed ~20 applications or deploy across 3+ clusters, the app-of-apps pattern becomes unwieldy. ApplicationSets use generator templates to create applications dynamically from Git directories, cluster lists, or matrix combinations.

See [ApplicationSets Reference](#reference-applicationsets) for generator types, production safety settings, and migration guidance.

### Multi-cluster management

ArgoCD can manage applications across multiple clusters from a single control plane:

```bash
# Register a target cluster
argocd cluster add <context-name>

# List registered clusters
argocd cluster list

# Create an app targeting a specific cluster
argocd app create <app> \
  --dest-server <cluster-api-url> \
  --dest-namespace <namespace> \
  ...
```

For multi-cluster at scale, combine with ApplicationSets using the Cluster generator. See [ApplicationSets Reference](#reference-applicationsets).

## Reference Files

Load these reference files on demand based on what the user is asking about. Do not load all references at once.

### Reference: Authentication
<a id="reference-authentication"></a>

When the user asks about logging in, setting up tokens, configuring auth for CI/CD, using core mode, switching ArgoCD contexts, managing project-scoped role tokens, or changing the admin password, read `references/authentication.md`.

### Reference: Sync Strategies
<a id="reference-sync-strategies"></a>

When the user asks about automated vs manual sync, self-heal, auto-prune, sync waves, sync hooks (PreSync/PostSync/SyncFail), resource ordering during sync, force sync, apply-out-of-sync-only, or choosing a sync strategy, read `references/sync-strategies.md`.

### Reference: Rollback Procedures
<a id="reference-rollback-procedures"></a>

When the user needs to undo a deployment, roll back to a previous version, inspect deployment history, or recover from a bad sync, read `references/rollback-procedures.md`.

### Reference: ApplicationSets
<a id="reference-applicationsets"></a>

When the user asks about ApplicationSets, generator types, managing many applications dynamically, migrating from app-of-apps, or multi-cluster application templating, read `references/applicationsets.md`.

### Reference: RBAC Configuration
<a id="reference-rbac-configuration"></a>

When the user asks about AppProject setup, role-based access control, restricting sync permissions, creating project-scoped roles, deny-all policies, or isolating teams within ArgoCD, read `references/rbac-configuration.md`.

### Reference: Troubleshooting
<a id="reference-troubleshooting"></a>

When the user reports an application stuck in OutOfSync, Degraded, Progressing, or Unknown state, or needs to diagnose sync failures, resource errors, manifest comparison issues, or wants to hard-refresh application state, read `references/troubleshooting.md`.

## Project and Resource Management

### Manage projects

```bash
# List projects
argocd proj list

# Get project details
argocd proj get <project-name>

# Create a project with source and destination restrictions
argocd proj create <project-name> \
  --src <allowed-repo-url> \
  --dest <cluster-url>,<namespace>
```

Projects provide RBAC isolation. See [RBAC Reference](#reference-rbac-configuration) for role setup.

### Manage repositories

```bash
# Add a Git repository
argocd repo add <repo-url> --username <user> --password <token>

# Add a Helm repository
argocd repo add <repo-url> --type helm --name <repo-name>

# List configured repositories
argocd repo list
```

### Resource inspection

```bash
# List resources managed by an app
argocd app resources <app-name>

# View logs for a specific resource
argocd app logs <app-name> --kind Deployment --name <deployment-name>

# View resource tree
argocd app resources <app-name> --tree
```
