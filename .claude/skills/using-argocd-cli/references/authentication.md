# Argo CD Authentication

Self-contained reference for authenticating the `argocd` CLI. Loaded from the
"Authentication" section of `SKILL.md`.

## Token vs password

| Method | When | Notes |
|--------|------|-------|
| SSO / OIDC (`argocd login --sso`) | Interactive humans | Short-lived session token written to `~/.config/argocd/config`. Preferred for people. |
| Local account password | Bootstrap / break-glass only | The `admin` account and local accounts. Disable or rotate `admin` after bootstrap. |
| Auth token (`ARGOCD_AUTH_TOKEN`) | CI/CD, automation | Non-expiring or long-lived; scope it to a project role. Never echo or log it. |

Always prefer a token for automation and SSO for humans. Avoid embedding passwords in
scripts.

## `argocd login` and context management

```bash
argocd login argocd.example.com --sso
argocd login argocd.example.com --username admin --password "$PW"   # break-glass only
argocd login argocd.example.com --grpc-web                          # see --grpc-web below

argocd context                # list saved server contexts; '*' marks active
argocd context prod           # switch active context
argocd logout argocd.example.com
```

Each context maps a server to its credentials. Confirm the active context before any
mutating command — operating against the wrong cluster is a classic outage.

## `ARGOCD_AUTH_TOKEN` (non-interactive)

```bash
export ARGOCD_AUTH_TOKEN="$(cat /run/secrets/argocd-token)"
export ARGOCD_SERVER=argocd.example.com
argocd app list --grpc-web
```

With `ARGOCD_AUTH_TOKEN` + `ARGOCD_SERVER` set, commands need no prior `argocd login`.
Generate tokens via `argocd account generate-token --account <name>` or, for a
project-scoped role, `argocd proj role create-token <project> <role>`.

## `--core`

`--core` makes the CLI talk directly to the Kubernetes API server using your kubeconfig,
bypassing `argocd-server` (the API/gRPC service) entirely. Useful in-cluster or when the
API server is unreachable. It relies on Kubernetes RBAC against the Argo CD CRDs rather
than Argo CD's own RBAC.

```bash
argocd app sync my-app --core
```

## `--grpc-web`

`--grpc-web` tunnels the gRPC API over HTTP/1.1. Use it when Argo CD is exposed behind an
ingress/load balancer that does not support HTTP/2 gRPC. If you see opaque connection or
"transport" errors through an ingress, add `--grpc-web`.

## Project-scoped role tokens

The least-privilege pattern for automation: create a role on an AppProject, grant only
the needed policies, then mint a token for that role.

```bash
argocd proj role create my-proj ci-deployer
argocd proj role add-policy my-proj ci-deployer \
  --action sync --permission allow --object 'my-proj/*'
argocd proj role create-token my-proj ci-deployer --expires-in 720h
```

The resulting JWT is the value you place in `ARGOCD_AUTH_TOKEN`. Rotate on the expiry you
set. See `rbac.md` for how AppProject roles and policies are evaluated.
