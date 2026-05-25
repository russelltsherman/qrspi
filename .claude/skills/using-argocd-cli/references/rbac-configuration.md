# RBAC Configuration Reference

Purpose: Guide to ArgoCD role-based access control — AppProject isolation, project-scoped roles with JWT tokens, deny-all default policy, production sync restrictions, and role binding examples.

## Table of Contents

- [RBAC Model Overview](#rbac-model-overview)
- [AppProject Isolation](#appproject-isolation)
- [Deny-All Default Policy](#deny-all-default-policy)
- [Project-Scoped Roles](#project-scoped-roles)
- [Production Sync Restrictions](#production-sync-restrictions)
- [Global RBAC Policies](#global-rbac-policies)
- [SSO Group Mapping](#sso-group-mapping)
- [Verifying Permissions](#verifying-permissions)

## RBAC Model Overview

ArgoCD RBAC operates at two levels:

1. **Global RBAC** — Defined in the `argocd-rbac-cm` ConfigMap. Controls cluster-wide permissions for built-in roles and local accounts.
2. **Project RBAC** — Defined in AppProject specs. Controls per-project permissions via project-scoped roles and JWT tokens.

For most production setups, use Project RBAC. It provides natural isolation between teams and supports scoped tokens for CI/CD.

## AppProject Isolation

AppProjects are the primary isolation boundary in ArgoCD. Each project defines:

- Which Git repositories can be used as sources
- Which clusters and namespaces applications can deploy to
- What resource kinds are allowed or denied
- Project-scoped roles and their permissions

### Create a project

```bash
# Create a project with source and destination restrictions
argocd proj create team-backend \
  --src https://github.com/org/backend-services.git \
  --dest https://kubernetes.default.svc,backend-*

# Add additional allowed sources
argocd proj add-source team-backend https://github.com/org/shared-libs.git

# Add additional allowed destinations
argocd proj add-destination team-backend https://kubernetes.default.svc backend-staging
```

### Restrict resource types

```bash
# Allow only specific resource kinds
argocd proj allow-cluster-resource team-backend "" Namespace
argocd proj allow-namespace-resource team-backend "" Deployment
argocd proj allow-namespace-resource team-backend "" Service
argocd proj allow-namespace-resource team-backend "" ConfigMap
argocd proj allow-namespace-resource team-backend "" Secret

# Deny specific resource kinds (deny takes precedence)
argocd proj deny-cluster-resource team-backend rbac.authorization.k8s.io ClusterRole
argocd proj deny-cluster-resource team-backend rbac.authorization.k8s.io ClusterRoleBinding
```

### View project configuration

```bash
# Get full project details
argocd proj get team-backend

# List all projects
argocd proj list
```

## Deny-All Default Policy

The recommended production configuration starts from a deny-all baseline and explicitly grants permissions:

```bash
# In argocd-rbac-cm ConfigMap:
# policy.default: role:none
```

To set this via kubectl:

```bash
kubectl -n argocd patch configmap argocd-rbac-cm --type merge -p '{
  "data": {
    "policy.default": "role:none"
  }
}'
```

With deny-all, users and tokens have no permissions until explicitly granted. This prevents accidental privilege escalation when new features or resources are added to ArgoCD.

### Built-in roles

ArgoCD provides two built-in roles:

| Role | Permissions |
|------|------------|
| `role:readonly` | Read access to all resources |
| `role:admin` | Full access to all resources |

With deny-all default, even authenticated users get no access unless assigned a role.

## Project-Scoped Roles

Project roles define permissions within a specific AppProject. They are the recommended way to grant CI/CD pipelines access to sync applications.

### Create a role

```bash
# Create a role in a project
argocd proj role create team-backend deployer
```

### Add policies to a role

Policy format: `p, proj:<project>:<role>, <resource>, <action>, <project>/<object>, <allow|deny>`

```bash
# Allow the deployer role to sync any application in the project
argocd proj role add-policy team-backend deployer \
  --action sync \
  --permission allow \
  --object "*"

# Allow get (read) access to applications
argocd proj role add-policy team-backend deployer \
  --action get \
  --permission allow \
  --object "*"

# Allow the deployer to view application logs
argocd proj role add-policy team-backend deployer \
  --action action/apps/Deployment/restart \
  --permission allow \
  --object "*"
```

### Available actions

| Resource | Actions |
|----------|---------|
| applications | `get`, `create`, `update`, `delete`, `sync`, `override`, `action/<group>/<kind>/<action>` |
| repositories | `get`, `create`, `update`, `delete` |
| clusters | `get`, `create`, `update`, `delete` |
| projects | `get`, `create`, `update`, `delete` |
| logs | `get` |
| exec | `create` |

### Generate a JWT token for the role

```bash
# Generate a token (no expiration)
argocd proj role create-token team-backend deployer

# Generate a token with expiration
argocd proj role create-token team-backend deployer --expires-in 24h

# The command outputs the JWT token — save it securely
```

Use the token in CI/CD:

```bash
export ARGOCD_AUTH_TOKEN="<jwt-token>"
export ARGOCD_SERVER="argocd.example.com"
argocd app sync backend-api --grpc-web
```

### List and delete tokens

```bash
# List tokens for a role (shows token IDs, not the tokens themselves)
argocd proj role list-tokens team-backend deployer

# Delete a specific token by ID
argocd proj role delete-token team-backend deployer <token-id>
```

## Production Sync Restrictions

### Restrict who can sync production

Create a fine-grained role that allows reading but not syncing production apps:

```bash
# Create a read-only role for production
argocd proj role create team-backend prod-reader

# Allow get but not sync
argocd proj role add-policy team-backend prod-reader \
  --action get \
  --permission allow \
  --object "*"

# Explicitly deny sync (defense in depth)
argocd proj role add-policy team-backend prod-reader \
  --action sync \
  --permission deny \
  --object "*"
```

### Separate roles for staging vs production

A common pattern uses two projects with different roles:

```bash
# Staging project — CI/CD can sync freely
argocd proj create team-backend-staging \
  --src https://github.com/org/backend.git \
  --dest https://kubernetes.default.svc,backend-staging

argocd proj role create team-backend-staging ci-deployer
argocd proj role add-policy team-backend-staging ci-deployer \
  --action sync --permission allow --object "*"
argocd proj role add-policy team-backend-staging ci-deployer \
  --action get --permission allow --object "*"

# Production project — CI/CD can read but only humans sync
argocd proj create team-backend-prod \
  --src https://github.com/org/backend.git \
  --dest https://prod-cluster.example.com,backend-prod

argocd proj role create team-backend-prod ci-reader
argocd proj role add-policy team-backend-prod ci-reader \
  --action get --permission allow --object "*"
# No sync permission for CI — humans sync production manually
```

## Global RBAC Policies

For policies that span projects, use the `argocd-rbac-cm` ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
data:
  policy.default: role:none
  policy.csv: |
    # Group-based access
    g, dev-team, role:readonly
    g, platform-team, role:admin

    # Fine-grained policy
    p, role:ci-deployer, applications, sync, */*, allow
    p, role:ci-deployer, applications, get, */*, allow
```

### RBAC policy syntax

```
# Permission policy
p, <subject>, <resource>, <action>, <project>/<object>, <allow|deny>

# Group binding
g, <user-or-group>, <role>
```

Examples:

```
# Allow user alice to sync any app in project team-backend
p, alice, applications, sync, team-backend/*, allow

# Allow the dev-team group read access to all projects
p, role:dev-reader, applications, get, */*, allow
g, dev-team, role:dev-reader

# Deny a specific user from deleting applications
p, bob, applications, delete, */*, deny
```

## SSO Group Mapping

Map SSO groups (from OIDC, SAML, or Dex) to ArgoCD roles:

```yaml
# In argocd-rbac-cm
data:
  policy.csv: |
    g, sso-group:engineering, role:readonly
    g, sso-group:platform-admins, role:admin
    g, sso-group:ci-systems, role:ci-deployer
```

The SSO group names must match the group claims from your identity provider. Configure the group claim field in `argocd-cm`:

```yaml
# In argocd-cm
data:
  oidc.config: |
    name: Okta
    issuer: https://okta.example.com
    clientID: <client-id>
    clientSecret: $oidc.okta.clientSecret
    requestedScopes: ["openid", "profile", "email", "groups"]
```

## Verifying Permissions

```bash
# Check what the current user/token can do
argocd account can-i sync applications 'team-backend/*'
# Output: yes or no

argocd account can-i get applications '*/*'
# Output: yes or no

# Check for a specific application
argocd account can-i sync applications 'team-backend/backend-api'
```
