# Authentication Reference

Detailed authentication patterns for the ArgoCD CLI. Covers token-based auth, interactive login, context management, headless/CI environments, and project-scoped tokens.

## Interactive Login

```bash
# Standard login (prompts for password)
argocd login <server-address>

# Login with gRPC-web (use when behind HTTP proxy or load balancer)
argocd login <server-address> --grpc-web

# Login with SSO (opens browser for OIDC/SAML flow)
argocd login <server-address> --sso

# Login with username/password non-interactively
argocd login <server-address> --username admin --password <password>

# Skip TLS verification (dev/test only — never production)
argocd login <server-address> --insecure
```

After login, the CLI stores a session token in `~/.config/argocd/config`. This token expires based on server configuration (default: 24 hours).

## Verify Authentication

```bash
# Show current user info
argocd account get-user-info

# List accessible applications (tests both auth and RBAC)
argocd app list
```

## Context Management

ArgoCD supports multiple server contexts, similar to kubectl contexts.

```bash
# List all configured contexts
argocd context

# Switch to a different context
argocd context <context-name>

# Delete a context
argocd context <context-name> --delete
```

Contexts are stored in `~/.config/argocd/config`. Each context holds the server address and auth token for one ArgoCD server.

**When to use contexts:** If you manage applications across multiple ArgoCD servers (e.g., staging and production run separate ArgoCD instances), configure a context for each and switch between them.

## Token-Based Authentication

Token auth is the recommended approach for CI/CD and automation. Tokens are passed via environment variable — no login step required.

### Generate an Account Token

```bash
# Generate a token for the current account
argocd account generate-token

# Generate a token for a specific account
argocd account generate-token --account <account-name>

# Generate a token with expiration
argocd account generate-token --account <account-name> --expires-in 24h
```

### Use the Token

```bash
# Set the token as an environment variable
export ARGOCD_AUTH_TOKEN="<token-value>"

# All subsequent commands use this token (no login needed)
argocd app list --server <server-address> --grpc-web
```

When `ARGOCD_AUTH_TOKEN` is set, the CLI skips the local config file and authenticates directly with the token. The `--server` flag is required because there is no context to infer it from.

## Project-Scoped Role Tokens

For CI/CD, prefer project-scoped tokens over account tokens. Project-scoped tokens are limited to a specific AppProject's applications, following least-privilege.

```bash
# Create a role in a project
argocd proj role create <project-name> <role-name>

# Add permissions to the role
argocd proj role add-policy <project-name> <role-name> \
  --action get --permission allow --object "<project-name>/*"
argocd proj role add-policy <project-name> <role-name> \
  --action sync --permission allow --object "<project-name>/*"

# Generate a token for the project role
argocd proj role create-token <project-name> <role-name>
```

The resulting token can only access applications within the specified project. This is safer than account tokens, which may have broader access.

## Core Mode (In-Cluster)

When the ArgoCD CLI runs inside the same Kubernetes cluster as the ArgoCD server, use core mode to bypass the API server entirely:

```bash
# Core mode — talks directly to Kubernetes, no ArgoCD API server needed
argocd app list --core

# Useful for CronJobs or controllers running in the argocd namespace
argocd app sync <app-name> --core
```

**Requirements for core mode:**
- The CLI must run in a Pod with a ServiceAccount that has access to ArgoCD's Kubernetes resources
- The ArgoCD namespace must be discoverable (defaults to `argocd`)
- No `ARGOCD_AUTH_TOKEN` or login is needed

**When to use core mode:** Kubernetes CronJobs, operators, or init containers that manage ArgoCD applications from within the cluster. Core mode eliminates the network hop to the ArgoCD API server.

## gRPC-Web Transport

ArgoCD uses gRPC (HTTP/2) by default. Many load balancers, proxies, and ingress controllers do not support HTTP/2 end-to-end. Use `--grpc-web` to downgrade to HTTP/1.1:

```bash
# Add --grpc-web to any command
argocd login <server-address> --grpc-web
argocd app list --grpc-web

# Or set it globally via environment variable
export ARGOCD_GRPC_WEB=true
```

**When to use `--grpc-web`:** Always use it when accessing ArgoCD through an ingress controller (nginx, ALB, Istio). Only omit it when connecting directly to the ArgoCD server on its native gRPC port.

## Initial Admin Password

On a fresh ArgoCD installation, the initial admin password is stored in a Kubernetes Secret:

```bash
# Retrieve the initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d

# Login with the initial password
argocd login <server-address> --username admin --password <initial-password>

# Change the password immediately
argocd account update-password \
  --current-password <initial-password> \
  --new-password <new-password>

# Delete the initial password secret (it is no longer needed)
kubectl -n argocd delete secret argocd-initial-admin-secret
```

**Always change the initial admin password** after first login. The initial secret is well-known and should be removed after password rotation.

## Environment Variables Reference

| Variable | Purpose |
|----------|---------|
| `ARGOCD_AUTH_TOKEN` | Auth token (skips login, requires `--server`) |
| `ARGOCD_SERVER` | Default server address (avoids `--server` on every command) |
| `ARGOCD_GRPC_WEB` | Set to `true` to use gRPC-web transport globally |
| `ARGOCD_OPTS` | Default CLI flags appended to every command |

## Troubleshooting Authentication

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `rpc error: code = Unauthenticated` | Token expired or invalid | Re-login or regenerate token |
| `dial tcp: connection refused` | Server not reachable | Check server address and network path |
| `transport: Error while dialing` | gRPC transport mismatch | Add `--grpc-web` flag |
| `permission denied` | RBAC denies the action | Check project role permissions |
| `x509: certificate signed by unknown authority` | TLS cert not trusted | Add CA to system trust store or use `--grpc-web` with TLS termination at ingress |
