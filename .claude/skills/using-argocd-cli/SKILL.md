---
name: using-argocd-cli
description: "Use the argocd CLI to operate Argo CD GitOps continuous delivery: authenticate and switch server contexts, create/get/diff/sync/wait/delete Applications, choose sync strategies, monitor app health, roll back bad deploys, manage app-of-apps and ApplicationSets, and configure RBAC/Projects. Use when the user works with Argo CD, the argocd CLI, GitOps app sync, ApplicationSets, or Argo CD rollbacks. Trigger on phrases like 'argocd app', 'sync my app', 'argocd login', 'GitOps deploy', 'ApplicationSet', 'argocd rollback', or 'Argo CD project/RBAC'."
command: /using-argocd-cli
argument-hint: <argocd task, e.g. "sync payments-prod" or "set up CI auth">
allowed-tools: Bash
---

# Using the Argo CD CLI

Operate Argo CD declaratively from the `argocd` CLI. Argo CD is a GitOps controller:
**Git is the source of truth**, and the CLI's job is to inspect, reconcile, and
occasionally override the relationship between desired state (Git) and live state
(the cluster). Sections below run simple → complex; jump to the one you need and follow
its `references/` pointer for deep material.

## Authentication & Context

Authenticate before anything else. Two audiences: an interactive developer wanting a
persisted session, or CI/CD automation driven entirely by environment variables.

```bash
# Interactive (human at a terminal)
argocd login argocd.example.com --sso
argocd context argocd.stg.example.com   # switch between saved servers

# Automation (no prompt, no disk session)
export ARGOCD_SERVER=argocd.example.com
export ARGOCD_AUTH_TOKEN=<project-scoped-token>
export ARGOCD_OPTS="--grpc-web"   # global flags applied to every call
argocd app list
```

**Prefer project-scoped API token auth over username/password for any non-interactive
or shared use.** Passwords are long-lived and broadly privileged; project role tokens are
scoped and revocable. `--grpc-web` is usually required behind an ingress; `--core` talks
straight to the Kubernetes API and skips the Argo CD API server.

For token vs password tradeoffs, `ARGOCD_*` env vars, `--grpc-web`/`--core`, role tokens,
and the interactive-vs-CI contrast, see `references/authentication.md`.

## Application Lifecycle

The core loop: create an app, review the diff, sync it, wait for health, and eventually
delete it. This covers the full create → sync → monitor → delete path.

```bash
# Create
argocd app create payments-prod \
  --repo https://github.com/acme/payments-manifests.git \
  --path overlays/prod \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace payments \
  --project payments

# Inspect & review before changing the cluster
argocd app get payments-prod          # status, health, sync state
argocd app diff payments-prod         # desired (Git) vs live (cluster)

# Apply desired state, then block until it settles
argocd app sync payments-prod
argocd app wait payments-prod --health --timeout 300

# Tear down (removes the app and, by default, its managed resources)
argocd app delete payments-prod
```

`get` and `diff` are read-only — run them before every `sync` in production so you know
exactly what will change. `wait --health` turns a fire-and-forget sync into a gated step
suitable for a pipeline.

## Sync Strategies

How desired state reaches the cluster: manually (a human gate) or automatically (applied
on drift). Tune with `--self-heal`, `--auto-prune`, `--dry-run`, sync waves, hooks, and a
retry policy.

```bash
argocd app sync payments-stg --dry-run                # preview, no changes
argocd app set payments-stg --sync-policy automated   # auto-apply on drift
argocd app set payments-stg --self-heal --auto-prune  # enforce + clean up
```

**Use manual sync for production; reserve automated sync for lower environments.**
Production should keep a deliberate promotion gate rather than auto-applying every merge.

For manual vs automated detail, `--self-heal`/`--auto-prune`, dry-run, sync waves, hooks,
`--force`/`--prune` cautions, `--apply-out-of-sync-only`, and retry policy, see
`references/sync-strategies.md`.

## Health Monitoring

After syncing, confirm the app is actually healthy — `Synced` (desired == live) is not the
same as `Healthy` (workloads running correctly).

```bash
argocd app get payments-prod              # Sync Status + Health Status at a glance
argocd app resources payments-prod        # per-resource health breakdown
argocd app wait payments-prod --health    # block until Healthy (or timeout)
argocd app list -o wide                   # fleet-wide health overview
```

Treat `Degraded` or stuck `Progressing` as the signal to drill in (see Troubleshooting).
When deep diagnosis is needed — events, logs, manifest compare, hard refresh — jump to
`references/troubleshooting.md`.

## Rollbacks

When a deploy goes bad, you can roll the live cluster back to a previous synced
revision — but that does not change Git.

```bash
argocd app history payments-prod              # find a known-good history id
argocd app rollback payments-prod <id>        # emergency: roll live back NOW
# then fix Git so the bad revision can't return:
git revert <bad-sha> && git push
argocd app sync payments-prod
```

**Prefer a Git revert over `argocd app rollback`.** A `rollback` changes only live state
and **auto-disables automated sync**; Git still points at the bad revision, so the next
sync re-applies it. Use `rollback` as a stopgap and always follow with a Git revert.

For the emergency procedure, the auto-disable behavior, `app history`, and the required
Git follow-up, see `references/rollback-procedures.md`.

## App-of-Apps

The app-of-apps pattern is a single parent Application whose rendered manifests are
*themselves* child Applications — a way to bootstrap and manage a fixed set of apps from
one Git path.

```bash
argocd app create platform-bootstrap \
  --repo https://github.com/acme/platform.git \
  --path apps \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace argocd
argocd app sync platform-bootstrap   # creates/updates all child apps
```

Use app-of-apps for a small, hand-curated, mostly static set. Once you are templating the
same app across many environments or clusters, graduate to an ApplicationSet — the
threshold and tradeoffs are in `references/applicationset-generators.md`.

## ApplicationSets

An ApplicationSet templates many Applications from generators (List, Git, Cluster,
Matrix), adding and removing apps automatically as clusters register or Git directories
appear.

```bash
argocd appset list
argocd appset get payments-fleet
argocd appset create applicationset.yaml   # apply an ApplicationSet manifest
```

By default, removing a generated entry deletes its Application and live resources; set
`preserveResourcesOnDeletion: true` to keep workloads running when an entry leaves the
set.

For Git/Cluster/Matrix/List generators, the app-of-apps → ApplicationSet transition
thresholds, and `preserveResourcesOnDeletion`, see
`references/applicationset-generators.md`.

## RBAC & Projects

AppProjects scope which repos, destinations, and resource kinds an app may use; RBAC
controls who may act on apps. Argo CD's default is deny-all.

```bash
argocd proj list
argocd proj create payments \
  --src https://github.com/acme/payments-manifests.git \
  --dest https://kubernetes.default.svc,payments-*
argocd proj role create-token payments ci --expires-in 720h
argocd admin settings rbac can role:payments-deployer sync 'payments/web'
```

Grant least privilege explicitly and never set a permissive default. For AppProjects,
project-scoped role tokens, `rbac validate`/`rbac can`, SSO group mapping, and the
deny-all default, see `references/rbac-configuration.md`.

## Multi-Cluster

Argo CD can deploy from one control plane to many target clusters. Register a cluster
once, then target it from an app's destination.

```bash
argocd cluster add <kube-context>      # register a cluster (uses your kubeconfig context)
argocd cluster list                    # registered clusters + connection status
# target a registered cluster by server URL in app create:
argocd app create web-eu \
  --dest-server https://eu.k8s.example.com \
  --dest-namespace web --repo ... --path ...
```

Registered clusters become the input to the Cluster and Matrix ApplicationSet generators
(`references/applicationset-generators.md`) for fanning one app across the whole fleet.

## Troubleshooting

When an app is stuck, `OutOfSync` for unclear reasons, or `Degraded`, work a fixed flow:
`app get` → `app resources` → events/logs → `terminate-op`.

```bash
argocd app get payments-prod              # 1. localize: sync + health + last op
argocd app resources payments-prod        # 2. find the one bad resource
argocd app diff payments-prod             # compare live vs Git when OutOfSync
argocd app get payments-prod --hard-refresh   # clear cache if Git changed but app didn't
argocd app terminate-op payments-prod     # cancel a wedged sync operation
```

If an app renders `Unknown`/`Missing`, check repo connectivity (`argocd repo list`)
before debugging manifests. For the full diagnostic flowchart, manifest live-vs-git
compare, hard refresh, and repo checks, see `references/troubleshooting.md`.
