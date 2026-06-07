# krew Plugin Catalog

`krew` is the kubectl plugin manager. Install it first, then add plugins from the
centralized index. Plugins extend `kubectl` with sub-commands invoked as
`kubectl <plugin>`.

## Provenance and trust

- Install only from the official krew-index (`kubectl krew index list` shows the
  configured indexes; the default `default` index points at the official
  `kubernetes-sigs/krew-index` catalog).
- Inspect a plugin before installing: `kubectl krew info <plugin>` shows the
  upstream homepage, version, and platform binaries.
- Treat third-party / custom krew indexes as untrusted code execution — review the
  source repo before adding an index with `kubectl krew index add <name> <url>`.
- Keep plugins current: `kubectl krew upgrade` (all) or `kubectl krew upgrade <plugin>`.
- A plugin is just a binary on `PATH` named `kubectl-<name>`; `kubectl plugin list`
  audits everything resolvable, including non-krew binaries.

## Core navigation plugins

| Plugin | Install | Purpose |
|--------|---------|---------|
| `ctx` | `kubectl krew install ctx` | Switch between kubeconfig contexts: `kubectl ctx <context>` |
| `ns` | `kubectl krew install ns` | Switch the active namespace: `kubectl ns <namespace>` |

> `ctx`/`ns` change persistent kubeconfig state. Confirm the active context
> (`kubectl ctx -c` / `kubectl config current-context`) before any mutating command.

## Inspection / output plugins

| Plugin | Install | Purpose |
|--------|---------|---------|
| `neat` | `kubectl krew install neat` | Strip managed/server-set fields from `get -o yaml`: `kubectl get <kind> <name> -o yaml \| kubectl neat` |
| `tree` | `kubectl krew install tree` | Show ownerReference hierarchy: `kubectl tree <kind> <name>` |
| `images` | `kubectl krew install images` | List container images in use: `kubectl images -n <namespace>` |

## Identity / RBAC plugins

| Plugin | Install | Purpose |
|--------|---------|---------|
| `whoami` | `kubectl krew install whoami` | Show the identity the current request authenticates as: `kubectl whoami` |
| `access-matrix` | `kubectl krew install access-matrix` | Render an RBAC access matrix for a subject: `kubectl access-matrix --sa <namespace>:<serviceaccount>` |

See `rbac-debugging.md` for how `whoami` and `access-matrix` slot into an RBAC
investigation.
