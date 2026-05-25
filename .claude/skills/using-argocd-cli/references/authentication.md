# Authentication Reference

Purpose: Comprehensive guide to ArgoCD CLI authentication patterns — interactive login, token-based auth, core mode, context management, and project-scoped role tokens.

## Interactive Login

The standard login flow for developer use at a terminal:

```bash
# Login with username/password
argocd login <argocd-server> --username admin --password <password>

# Login with SSO (opens browser)
argocd login <argocd-server> --sso

# Login with SSO in headless environments (prints URL to visit)
argocd login <argocd-server> --sso --sso-port 0
```

Login creates a session token stored in `~/.config/argocd/config` (or `~/.argocd/config` on older versions). The session expires based on server-side configuration (default: 24 hours).

### Verify authentication

```bash
# Check current auth status
argocd account get-user-info

# If this errors, you need to re-login
```

## Initial Admin Password

On a fresh ArgoCD installation, the initial admin password is stored in a Kubernetes secret:

```bash
# Retrieve the initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# Change the admin password (do this immediately after first login)
argocd account update-password \
  --current-password <initial-password> \
  --new-password <new-password>
```

After changing the password, delete the initial secret:

```bash
kubectl -n argocd delete secret argocd-initial-admin-secret
```

## Token-Based Authentication

For CI/CD pipelines and automation, use token-based auth instead of interactive login.

### API token for local accounts

```bash
# Generate a token for a local account
argocd account generate-token --account <account-name>

# Use the token
export ARGOCD_AUTH_TOKEN="<token>"
argocd app list  # uses token automatically
```

### Project-scoped role tokens

Project-scoped tokens are the recommended approach for CI/CD. They limit the token's permissions to a specific project's resources.

```bash
# Create a role in a project (if not already defined in project spec)
argocd proj role create <project> <role-name>

# Add a policy to the role
argocd proj role add-policy <project> <role-name> \
  --action get --permission allow --object "*"
argocd proj role add-policy <project> <role-name> \
  --action sync --permission allow --object "*"

# Generate a token for the role
argocd proj role create-token <project> <role-name>
```

The resulting token can only perform actions allowed by the role's policies within the specified project. See the RBAC reference for policy syntax.

### Token usage in CI/CD

```bash
# Set as environment variable (preferred)
export ARGOCD_AUTH_TOKEN="$ARGOCD_TOKEN_FROM_CI_SECRETS"
export ARGOCD_SERVER="argocd.example.com"

# Or pass directly (less preferred — token appears in process list)
argocd app sync <app> --auth-token <token> --server <server>
```

## Context Management

ArgoCD CLI supports multiple server contexts, similar to kubectl contexts:

```bash
# List configured contexts
argocd context

# Switch to a different context
argocd context <context-name>

# Add a new context (happens automatically on login)
argocd login <new-server> --name <context-name>

# Delete a context
argocd context --delete <context-name>
```

Contexts are stored in `~/.config/argocd/config`. Each context stores the server address and auth token for that server.

### Using a specific context without switching

```bash
# Target a specific server for a single command
argocd app list --server <argocd-server>
```

## Core Mode

Core mode lets the ArgoCD CLI talk directly to the Kubernetes API instead of going through the ArgoCD API server. This is useful when:

- You have `kubectl` access to the cluster running ArgoCD
- The ArgoCD API server is not exposed externally
- You want to avoid network hops in CI/CD runners on the same cluster

```bash
# Use core mode for a single command
argocd app list --core

# Set core mode as default in kubeconfig context
argocd app list --core --kube-context <context-name>
```

In core mode:
- No `ARGOCD_SERVER` or `ARGOCD_AUTH_TOKEN` needed
- Authentication uses your kubeconfig credentials
- RBAC is governed by Kubernetes RBAC, not ArgoCD RBAC
- The ArgoCD API server does not need to be running

### Core mode in CI/CD

```bash
# CI/CD runner with service account on the ArgoCD cluster
argocd app sync <app> --core --kube-context <context>
argocd app wait <app> --core --health --timeout 300
```

This eliminates the need for ArgoCD tokens entirely. The CI runner's Kubernetes service account must have appropriate RBAC permissions on the ArgoCD CRDs.

## gRPC-Web

By default, ArgoCD CLI uses gRPC for communication. Some network environments (HTTP proxies, certain load balancers) do not support gRPC. Use `--grpc-web` to tunnel gRPC over HTTP/1.1:

```bash
# Single command with grpc-web
argocd app list --grpc-web

# Login with grpc-web (sets it for the context)
argocd login <server> --grpc-web
```

If you consistently need `--grpc-web`, set it during login so it applies to all subsequent commands for that context.

### When to use gRPC-web

- Behind an HTTP load balancer that does not support HTTP/2 (e.g., ALB without gRPC target group)
- Behind a corporate proxy that strips HTTP/2 frames
- When you see errors like `transport: error while dialing: dial tcp: connection refused` but the server is reachable via HTTPS

## TLS Configuration

```bash
# Skip TLS verification (not recommended for production)
argocd login <server> --insecure

# Use a custom CA certificate
argocd login <server> --certificate-authority-data <base64-ca>

# Or reference a CA file
argocd login <server> --ca-cert <path-to-ca.crt>
```

Use `--insecure` only when TLS is terminated by a trusted upstream component (e.g., an ingress controller with a valid cert). Never use `--insecure` when connecting over untrusted networks.

## Environment Variables

All connection parameters can be set via environment variables:

| Variable | Purpose |
|----------|---------|
| `ARGOCD_SERVER` | ArgoCD server address (host:port) |
| `ARGOCD_AUTH_TOKEN` | Authentication token (bypasses login) |
| `ARGOCD_OPTS` | Additional CLI flags applied to all commands |
| `ARGOCD_GRPC_WEB` | Set to `true` to use gRPC-web by default |
| `ARGOCD_INSECURE` | Set to `true` to skip TLS verification |

Example CI/CD configuration:

```bash
export ARGOCD_SERVER="argocd.example.com"
export ARGOCD_AUTH_TOKEN="$CI_ARGOCD_TOKEN"
export ARGOCD_GRPC_WEB="true"
```
