---
name: using-argocd-cli
description: "Drive Argo CD GitOps continuous delivery from the command line — authenticate, create/diff/sync/monitor/rollback/delete Applications, and escalate to multi-cluster ApplicationSets. Use when the user wants to interact with Argo CD via the `argocd` CLI (e.g., 'sync my-app in argocd', 'why is my argocd app OutOfSync', 'roll back the prod app', 'log into argocd', 'create an argocd application'). Trigger on any variant referencing argocd, Argo CD, GitOps sync/diff/rollback, Application/AppProject/ApplicationSet management, or app health/sync status. OUT OF SCOPE: general (non-Argo-CD) Kubernetes automation, raw `kubectl` workflows unrelated to Argo CD, Argo Workflows/Events/Rollouts (a different product), and Helm/Kustomize templating done outside Argo CD."
command: /using-argocd-cli
argument-hint: <app-name or natural-language argocd request>
allowed-tools: Bash(argocd:*), Bash(kubectl:*), Read
---

# Using the Argo CD CLI

You drive Argo CD (GitOps continuous delivery) through the `argocd` CLI. Argo CD's
source of truth is Git: the desired state lives in a repo, and Argo CD reconciles the
live cluster toward it. Your job is to operate that reconciliation safely — favor
declarative, Git-backed changes over imperative cluster mutations, and never take a
destructive shortcut without explicit confirmation.

Work through the lifecycle stages below in order when handling an end-to-end request.
For deep detail on any stage, load exactly the one reference file pointed to in that
section — do not pre-load references you do not need.

## When to use / out of scope

Use this skill when the request targets Argo CD: authenticating to an Argo CD server,
managing Applications/AppProjects/ApplicationSets, inspecting sync or health status,
diffing live-vs-desired state, syncing, rolling back, or deleting Argo CD-managed apps.

This skill does **not** cover:

- General Kubernetes automation that is not mediated by Argo CD (use plain `kubectl`
  outside this skill).
- Argo Workflows, Argo Events, or Argo Rollouts — these are separate products with
  different CLIs (`argo`, not `argocd`).
- Helm/Kustomize authoring or templating performed outside an Argo CD Application.

`kubectl` is available here only as a read-only follow-up for debugging Argo CD-managed
resources (e.g. `kubectl describe` a pod an Application created), never as a way to
mutate state Argo CD owns.

## Authentication

Argo CD has two distinct auth contexts. Determine which you are in before running any
command.

**Interactive (a human at a terminal):**

```bash
argocd login <ARGOCD_SERVER> --sso          # or --username/--password for local accounts
argocd context                              # list/switch between saved server contexts
argocd context <name>                       # set the active context
```

Prefer SSO or a short-lived session over storing a password.

**CI/CD or non-interactive automation:**

```bash
export ARGOCD_AUTH_TOKEN=<project-scoped-token>   # never echo or log this value
argocd app list --server <ARGOCD_SERVER> --grpc-web
argocd app sync my-app --core                      # --core talks to the cluster API directly, no argocd-server
```

Use a token, not a username/password, for automation. Scope the token to the narrowest
AppProject role that works.

Read `references/authentication.md` for token vs password, `--grpc-web`, and
project-scoped role tokens.

## Create application

Prefer a **declarative** Application manifest committed to Git over an imperative
`argocd app create`. The declarative form is reviewable, reproducible, and itself
GitOps-managed (app-of-apps).

```bash
# Preferred: commit an Application manifest, then let Argo CD adopt it.
kubectl apply -f application.yaml -n argocd      # or sync it via a parent app-of-apps

# Imperative (acceptable for throwaway/dev only):
argocd app create my-app \
  --repo https://github.com/org/repo.git \
  --path manifests/ \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace my-ns
```

State the destination cluster and namespace explicitly. Do not enable automated sync at
creation time for production targets (see Defaults below).

## Diff & sync

Always diff before you sync, and choose the sync mode by environment.

```bash
argocd app diff my-app          # live vs desired; exits non-zero if drift exists
argocd app sync my-app          # apply desired state
argocd app sync my-app --dry-run
```

| Target environment | Sync strategy | Why |
|--------------------|---------------|-----|
| Production         | **Manual sync** (review diff, then `argocd app sync`) | Human gate on every change; no surprise reconciliation |
| Staging / pre-prod | Manual or automated **without** self-heal | Catch drift but keep a person aware |
| Dev / ephemeral    | Automated sync (optionally self-heal/prune) | Fast iteration, low blast radius |

Never reach for `--force` or `--prune` to push past a failed or drifting sync without
reading the cautions first.

Read `references/sync-strategies.md` for self-heal, sync waves, hooks, retry, and
`--force`/`--prune` cautions.

## Monitor

Inspect health and sync status before declaring a change successful.

```bash
argocd app get my-app                   # summary: sync status, health, resources
argocd app list                         # all apps with sync/health columns
argocd app resources my-app             # per-resource health
argocd app wait my-app --health --sync  # block until Healthy + Synced (or timeout)
argocd app history my-app               # deployment revisions (input to rollback)
```

A successful change is `Synced` **and** `Healthy`. `Synced` alone (e.g. `Progressing`
or `Degraded` health) is not done.

## Rollback

Encode the GitOps default: revert in Git, not in the cluster.

**Do:**

1. Revert the offending commit in the source repo, then `argocd app sync my-app`. Git
   stays the source of truth and history is auditable.
2. Inspect `argocd app history my-app` to identify the last-good revision before acting.
3. For an emergency where Git revert is too slow, use `argocd app rollback my-app <id>`
   — but immediately follow up by reconciling Git to match, or the next sync re-applies
   the bad state.

**Don't:**

1. Don't `argocd app rollback` and walk away — an unreverted Git source will drift the
   app right back on the next reconcile.
2. Don't `kubectl edit`/`kubectl rollout undo` Argo CD-managed resources; Argo CD will
   overwrite your change and you lose the audit trail.

Read `references/rollback.md` for git revert vs `argocd app rollback`, history
inspection, and auto-rollback-on-degraded.

## Delete

Deletion is destructive — confirm intent and choose the propagation policy deliberately.

```bash
argocd app delete my-app                          # default cascade: also deletes child resources
argocd app delete my-app --cascade=false          # remove the Application only, leave live resources
argocd app delete my-app --propagation-policy=foreground
```

Cascade delete removes the live workloads the app manages. Confirm with the user before a
cascade delete of anything non-ephemeral. Watch for stuck finalizers — a Deletion that
hangs usually means a finalizer is blocking; investigate rather than force-removing it.

## Escalation: simple → multi-cluster

Start simple. Escalate the management pattern only when scale demands it.

| Situation | Pattern | Tooling |
|-----------|---------|---------|
| A handful of apps, one cluster | Individual Applications | `argocd app create` / declarative manifests |
| Many related apps, one cluster | **app-of-apps** (a parent Application that syncs child Application manifests) | declarative |
| > ~20 apps, or > ~3 clusters, or templated fan-out | **ApplicationSet** (generators template Applications) | `ApplicationSet` CR |

Do not hand-roll dozens of near-identical Application manifests; that is the signal to
move to an ApplicationSet generator.

Read `references/applicationsets.md` for generators (Git/Cluster/Matrix/List),
app-of-apps, and `preserveResourcesOnDeletion`.

## RBAC & permissions

Argo CD defaults to **deny-all**; permissions are granted through AppProjects and RBAC
policy. When a command fails with a permission error, this is the first place to look.

Read `references/rbac.md` for AppProjects, JWT role tokens, `rbac validate`/`can`, SSO
mapping, and the deny-all default.

## Troubleshooting

When a sync fails, an app is stuck, or health is `Degraded`/`Unknown`, work the
debugging flow rather than guessing.

Read `references/troubleshooting.md` for the debugging flowchart, `terminate-op`, hard
refresh, live-vs-git manifests, repo connectivity, and scoped `kubectl describe`/logs
follow-ups.

## HARD STOP

Stop and get explicit human confirmation before doing any of the following. Do not "just
try one thing" — these are exactly the actions that cause irreversible damage.

- **`--force` or `--prune` on a sync.** `--force` overwrites/deletes-and-recreates
  resources; `--prune` deletes live resources absent from Git. Never use either to push
  past a failed or drifting sync without confirming the blast radius.
- **Cascade delete (`argocd app delete` without `--cascade=false`) of any non-ephemeral
  app.** This destroys the live workloads, not just the Application record.
- **Authentication or cluster-access failures.** Token expired, login refused, context
  pointing at the wrong cluster, or a permission denial. STOP and report the exact error.
  Do not retry with broader scope, switch contexts blindly, or work around it.
- **Repeated sync failures.** After one diagnostic pass, if a sync still fails, STOP and
  report the error and your hypothesis. Do not escalate to `--force`/`--prune` to "make
  it go green."

If any command fails with an auth, permission, or cluster-access error, print the exact
failing command and the exact error output, then stop. Report which side (your action vs
upstream/cluster) you believe is at fault.

## Defaults (do / don't)

1. **Manual sync for production.**
   - Do: review `argocd app diff`, then `argocd app sync` with a human in the loop.
   - Don't: enable automated sync + self-heal on a production target by default.
2. **Git revert over imperative rollback.**
   - Do: revert the commit and re-sync so Git stays the source of truth.
   - Don't: rely on `argocd app rollback` alone — unreverted Git drifts it back.
3. **Token auth over password.**
   - Do: use a project-scoped `ARGOCD_AUTH_TOKEN` for automation.
   - Don't: store or pass a username/password in scripts or CI.
