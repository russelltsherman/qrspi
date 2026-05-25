# RBAC Configuration Reference

Guide to ArgoCD's RBAC model: AppProject isolation, project-scoped roles, JWT tokens, and production access restrictions.

## RBAC Model Overview

ArgoCD uses a two-layer access control model:

1. **AppProjects** — Define which Git repositories, clusters, and namespaces an Application can target. This is resource-level isolation.
2. **RBAC Policies** — Define which users/roles can perform which actions on which resources. This is user-level access control.

Both layers must allow an operation for it to succeed.

## AppProject Isolation

### Create a Project with Restrictions

```bash
# Create a project that restricts source repos and destination clusters
argocd proj create team-frontend \
  --description "Frontend team applications" \
  --src "https://github.com/org/frontend-*" \
  --dest "https://kubernetes.default.svc,frontend-*"
```

### Configure Allowed Sources

```bash
# Add an allowed source repository
argocd proj add-source team-frontend https://github.com/org/frontend-app

# Remove a source
argocd proj remove-source team-frontend https://github.com/org/old-repo

# List current sources
argocd proj get team-frontend
```

### Configure Allowed Destinations

```bash
# Add an allowed destination (cluster, namespace)
argocd proj add-destination team-frontend \
  https://kubernetes.default.svc frontend-prod

# Allow any namespace on a specific cluster
argocd proj add-destination team-frontend \
  https://kubernetes.default.svc "*"

# Remove a destination
argocd proj remove-destination team-frontend \
  https://kubernetes.default.svc frontend-staging
```

### Restrict Resource Types

```bash
# Allow only specific resource types
argocd proj allow-cluster-resource team-frontend "*" Namespace
argocd proj allow-namespace-resource team-frontend apps Deployment
argocd proj allow-namespace-resource team-frontend "" Service
argocd proj allow-namespace-resource team-frontend "" ConfigMap

# Deny specific resource types
argocd proj deny-cluster-resource team-frontend "*" ClusterRole
argocd proj deny-namespace-resource team-frontend rbac.authorization.k8s.io Role
```

## Default Policy: Deny-All

**Start with deny-all and add permissions explicitly.** The default ArgoCD RBAC policy can be configured in `argocd-rbac-cm` ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.default: role:none
  policy.csv: |
    # Deny everything by default
    p, role:none, *, *, */*, deny
```

With this policy, all access must be explicitly granted via project roles or global RBAC policies.

## Project-Scoped Roles

### Create a Role

```bash
# Create a role within a project
argocd proj role create team-frontend ci-deployer

# List roles in a project
argocd proj role list team-frontend
```

### Add Policies to a Role

Policies follow the format: `action permission object`

```bash
# Allow the ci-deployer role to get and sync applications in the project
argocd proj role add-policy team-frontend ci-deployer \
  --action get --permission allow --object "team-frontend/*"

argocd proj role add-policy team-frontend ci-deployer \
  --action sync --permission allow --object "team-frontend/*"

# Allow viewing application logs
argocd proj role add-policy team-frontend ci-deployer \
  --action get --permission allow --object "team-frontend/logs"
```

### Available Actions

| Action | Description |
|--------|------------|
| `get` | View application status, details, and resources |
| `create` | Create new applications |
| `update` | Modify application settings |
| `delete` | Delete applications |
| `sync` | Trigger sync operations |
| `override` | Override application parameters |
| `action` | Run resource actions (restart, scale) |

### Remove Policies

```bash
# Remove a specific policy
argocd proj role remove-policy team-frontend ci-deployer \
  --action sync --permission allow --object "team-frontend/*"

# Delete a role entirely
argocd proj role delete team-frontend ci-deployer
```

## JWT Tokens for Roles

Generate tokens scoped to a project role for CI/CD pipelines:

```bash
# Generate a token for a project role
argocd proj role create-token team-frontend ci-deployer

# Generate a token with expiration
argocd proj role create-token team-frontend ci-deployer --expires-in 90d

# List tokens for a role
argocd proj role get team-frontend ci-deployer
```

**Token best practices:**
- Set expiration (`--expires-in`) — never generate permanent tokens for CI/CD
- Use one token per pipeline/service — do not share tokens between systems
- Rotate tokens on a regular schedule (90 days or less)
- Revoke tokens when a pipeline is decommissioned

### Revoke Tokens

```bash
# Delete a specific token by its IAT (issued-at timestamp)
argocd proj role delete-token team-frontend ci-deployer <iat>
```

The IAT value is shown in the output of `argocd proj role get`.

## Production Sync Restrictions

### Read-Only Role for Production

```bash
# Create a read-only role
argocd proj role create production viewer

# Allow only get actions
argocd proj role add-policy production viewer \
  --action get --permission allow --object "production/*"

# Explicitly deny sync
argocd proj role add-policy production viewer \
  --action sync --permission deny --object "production/*"
```

### Restricted Deployer Role for Production

```bash
# Create a deployer role with limited sync permissions
argocd proj role create production deployer

# Allow get and sync, but not create/delete/update
argocd proj role add-policy production deployer \
  --action get --permission allow --object "production/*"
argocd proj role add-policy production deployer \
  --action sync --permission allow --object "production/*"

# Deny destructive operations
argocd proj role add-policy production deployer \
  --action delete --permission deny --object "production/*"
argocd proj role add-policy production deployer \
  --action create --permission deny --object "production/*"
```

### Sync Windows for Production

Combine RBAC with sync windows to restrict when production deployments can happen:

```bash
# Allow syncing only during the maintenance window
argocd proj windows add production \
  --kind allow \
  --schedule "0 2 * * 6" \
  --duration 4h \
  --applications "*"
```

## Global RBAC Policies

For policies that span all projects, configure `argocd-rbac-cm`:

```yaml
data:
  policy.csv: |
    # Platform team: full access to all projects
    p, role:platform-admin, applications, *, */*, allow
    p, role:platform-admin, clusters, *, *, allow
    p, role:platform-admin, projects, *, *, allow

    # Developers: read access to all, sync access to non-prod
    p, role:developer, applications, get, */*, allow
    p, role:developer, applications, sync, staging/*, allow
    p, role:developer, applications, sync, dev/*, allow
    p, role:developer, applications, sync, production/*, deny

    # Map SSO groups to roles
    g, org:platform-team, role:platform-admin
    g, org:developers, role:developer
```

## Verifying Permissions

```bash
# Check what a specific user/role can do
argocd admin settings rbac can role:developer get applications "production/*" \
  --policy-file <path-to-policy.csv>

# Validate the full RBAC policy
argocd admin settings rbac validate --policy-file <path-to-policy.csv>
```

## Troubleshooting RBAC

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `permission denied` on sync | Role lacks `sync` action on the target object | Add `sync` permission to the role |
| Can view apps but not sync | Read-only role or deny policy on sync | Check for explicit deny rules |
| App creation fails with "not permitted" | Project restricts source repo or destination | Add the repo/cluster/namespace to the project |
| Token works but returns empty app list | Token role has no `get` permission | Add `get` permission to the project role |
| SSO login works but no access | SSO group not mapped to an ArgoCD role | Add group mapping in `argocd-rbac-cm` |
