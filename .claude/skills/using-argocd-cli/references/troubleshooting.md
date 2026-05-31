# Argo CD Troubleshooting

Self-contained reference for diagnosing failed/stuck Applications. Loaded from the
"Troubleshooting" section of `SKILL.md`.

## Debugging flowchart

```
argocd app get <app>
        │
   Sync status?
        ├── OutOfSync ──► argocd app diff <app>          (what differs from Git?)
        │                   └── drift expected? sync. unexpected? find who/what changed live state.
        │
   Health status?
        ├── Degraded ──► argocd app resources <app>      (which resource is unhealthy?)
        │                   └── kubectl describe / logs that resource (read-only follow-up)
        ├── Progressing (stuck) ──► check sync waves/hooks; argocd app get --show-operation
        └── Unknown ──► repo/cluster connectivity (see below)
```

Work top-down: sync status first (is desired state even reaching the cluster?), then
health (did the applied resources come up?).

## Stuck operations: `terminate-op`

A sync that hangs (stuck hook, unreachable resource) blocks further operations.

```bash
argocd app get <app> --show-operation     # inspect the in-flight operation
argocd app terminate-op <app>             # cancel the stuck sync operation
```

Terminate, then re-diagnose — do not immediately re-sync the same broken input.

## Hard refresh

Argo CD caches the desired manifests. If Git changed but Argo CD does not see it, force a
re-fetch:

```bash
argocd app get <app> --hard-refresh
```

Use this when the diff looks stale relative to a known Git push.

## Live-vs-Git manifests

Compare exactly what Argo CD rendered against what is live:

```bash
argocd app manifests <app> --source git    # desired (rendered from Git)
argocd app manifests <app> --source live    # live in-cluster
argocd app diff <app>                        # the delta
```

This isolates "bad manifest" (git side wrong) from "drift" (live side changed).

## Repo connectivity

`Unknown` status or "failed to load target state" often means Argo CD cannot reach the
repo or cluster:

```bash
argocd repo list                  # connection status of configured repos
argocd repo get <repo-url>
argocd cluster list               # connection status of destination clusters
```

Fix credentials/network before retrying a sync.

## Scoped `kubectl` follow-ups (read-only)

Once `argocd app resources` names the unhealthy resource, drill in with `kubectl` —
**read-only**, scoped to that resource. Never mutate Argo CD-managed resources by hand
(it will be reverted and you lose the audit trail).

```bash
kubectl describe <kind>/<name> -n <ns>          # events, conditions
kubectl logs <pod> -n <ns> --follow             # follow application logs
kubectl get events -n <ns> --sort-by=.lastTimestamp
```

If diagnosis points to an auth, permission, or cluster-access failure, STOP and report
the exact error per the HARD STOP block in `SKILL.md` — do not work around it.
