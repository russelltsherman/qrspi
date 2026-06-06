# Troubleshooting

Deep reference for diagnosing a stuck, degraded, or out-of-sync Application. Loaded on
demand from the skill body's Troubleshooting section. Work the flow top to bottom; stop
at the first step that explains the symptom.

## Diagnostic flow

### 1. Start with `app get`

```bash
argocd app get payments-prod
```

Read three fields first: **Sync Status** (`Synced` / `OutOfSync`), **Health Status**
(`Healthy` / `Progressing` / `Degraded` / `Missing`), and the current **operation
state** (last sync result + message). This single command usually localizes the problem
to either a sync failure or a runtime health failure.

### 2. Drill into resources

```bash
argocd app resources payments-prod
```

Lists every managed resource with its individual sync and health status. Find the *one*
resource that is `Degraded`/`OutOfSync` rather than treating the whole app as a black
box. The failing resource name drives the next step.

### 3. Events and logs of the failing resource

```bash
# Kubernetes events explaining why a resource is unhealthy
argocd app get payments-prod --show-operation
kubectl describe <kind>/<name> -n <namespace>   # via --core or kubeconfig
kubectl logs <pod> -n <namespace>
```

Most `Degraded` causes (ImagePullBackOff, CrashLoopBackOff, failed probes, quota
denials) surface in the resource's events and pod logs.

### 4. Terminate a stuck operation

```bash
argocd app terminate-op payments-prod
```

If a sync is wedged (a hook Job never completes, a resource is stuck `Progressing`
forever), `terminate-op` cancels the in-flight operation so you can retry or roll back.
Use it when `app get` shows an operation that has been running far too long.

## Targeted checks

### Live-vs-Git manifest compare

```bash
argocd app diff payments-prod                       # rendered diff: live vs desired
argocd app manifests payments-prod --source live    # what is actually in the cluster
argocd app manifests payments-prod --source git     # what Git renders to
```

Use this when status says `OutOfSync` but the cause is non-obvious — the diff shows the
exact field drift (often an out-of-band `kubectl edit` or a mutating webhook).

### Hard refresh (clear the cache)

```bash
argocd app get payments-prod --hard-refresh
```

Argo CD caches rendered manifests and repo state. If Git clearly changed but the app
still shows the old state, a `--hard-refresh` forces a re-clone/re-render and clears the
cache before you chase a phantom bug.

### Repository connectivity

```bash
argocd repo list                       # connection status per repo
argocd repo get https://github.com/acme/payments-manifests.git
```

If an app is `Unknown`/`Missing` or refuses to render, confirm the source repo is
reachable and its credentials are valid before debugging manifests — a broken repo
connection masquerades as a manifest problem.
