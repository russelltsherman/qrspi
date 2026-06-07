# Authentication & Context

Deep reference for authenticating the `argocd` CLI to an Argo CD API server and
managing multiple server contexts. Loaded on demand from the skill body's
Authentication & Context section.

## Opinionated default

**Prefer project-scoped API token auth over username/password for any non-interactive
or shared use.** Passwords (especially the bootstrap `admin` account) are long-lived,
broadly privileged, and awkward to rotate; project-scoped role tokens are narrowly
scoped, revocable, and safe to store in CI secrets. Reserve password login for the
first-time interactive bootstrap only, then disable or rotate the `admin` account.

## Two auth modes

Argo CD CLI auth splits cleanly into two audiences. Decide which you are before
picking flags.

### Interactive developer

You are a human at a terminal who wants a persisted session.

```bash
# SSO browser flow (preferred when SSO is configured)
argocd login argocd.example.com --sso

# Username/password (bootstrap / break-glass only)
argocd login argocd.example.com --username admin

# Inspect / switch between saved server contexts
argocd context                 # list contexts, mark the current one
argocd context argocd.stg.example.com   # switch active context
```

`argocd login` writes the session token into `~/.config/argocd/config`. `argocd
context` lets one workstation hold sessions for several servers (dev/stg/prod) and
toggle between them without re-authenticating.

### CI/CD automation

No persisted session, no browser, no interactive prompt. Drive everything through
environment variables so nothing is written to disk and nothing prompts.

```bash
export ARGOCD_SERVER=argocd.example.com
export ARGOCD_AUTH_TOKEN=<project-scoped-token>
# Bundle global flags once instead of repeating them per command:
export ARGOCD_OPTS="--grpc-web"

argocd app list   # picks up server + token + opts from the environment
```

- `ARGOCD_SERVER` — host:port of the API server; replaces the positional arg to `login`.
- `ARGOCD_AUTH_TOKEN` — the bearer token; replaces an interactive session entirely.
- `ARGOCD_OPTS` — a catch-all for global flags (e.g. `--grpc-web --insecure`) applied
  to every invocation; ideal for pinning transport settings in a pipeline image.

## Transport flags

- `--grpc-web` — tunnels the gRPC API over HTTP/1.1. Required when the server sits
  behind an ingress/load balancer that does not speak HTTP/2 gRPC (the common case).
  If `argocd` calls hang or fail with transport errors behind an ingress, add this first.
- `--core` — talks **directly to the Kubernetes API**, bypassing the Argo CD API server
  entirely (no `argocd-server` deployment needed). Requires kube RBAC on the Argo CD
  CRDs/namespace. Useful for admin/operator workflows and clusters running Argo CD in
  "core" (server-less) mode.

## Project-scoped role tokens

Generate narrowly-scoped tokens tied to an AppProject role rather than handing out
account tokens. See `references/rbac-configuration.md` for the project/role setup.

```bash
# Create a token for the `ci` role in the `payments` project
argocd proj role create-token payments ci --expires-in 720h

# Account-level token (broader — avoid for CI; prefer project role tokens)
argocd account generate-token --account ci-bot
```

Store the resulting token as `ARGOCD_AUTH_TOKEN` in the pipeline secret store. Set
`--expires-in` so tokens rotate on a schedule rather than living forever.
