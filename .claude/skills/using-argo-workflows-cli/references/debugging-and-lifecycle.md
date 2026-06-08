# Debugging and lifecycle

A workflow failed, is stuck, or you need to act on one that is already running or
finished. Read this for the debugging escalation path, the common causes of
failure, and every command that changes a workflow's state after submission.

## Contents

- [Debugging escalation path](#debugging-escalation-path)
- [Common failure causes](#common-failure-causes)
- [`retry` — re-run from the failed node](#retry--re-run-from-the-failed-node)
- [`resubmit` — re-run from scratch](#resubmit--re-run-from-scratch)
- [`stop` vs `terminate`](#stop-vs-terminate)
- [`suspend` and `resume`](#suspend-and-resume)
- [`delete` — clean up](#delete--clean-up)

## Debugging escalation path

Debug in this order — each step narrows the search and only escalates when the
Argo-level view runs out of information. Jumping straight to `kubectl` wastes time
when `argo get` already names the failing node.

1. **`argo get <workflow>`** — read the node tree. Find the first node whose phase
   is `Failed` or `Error`. Its `message` field often states the cause outright
   (image pull error, non-zero exit, timeout). Note the node name.

   ```bash
   argo get @latest
   ```

2. **`argo logs <workflow> <node>`** — read that node's container output. A
   non-zero exit from your own command shows its stderr here.

   ```bash
   argo logs @latest <failing-node-name>
   ```

   If `main` logs are empty, the failure is before your code ran — check the
   `init` (input/artifact download) and `wait` (output/artifact upload)
   containers with `-c init` / `-c wait`.

3. **`kubectl describe pod <pod>`** — escalate here only when the failure is at the
   Kubernetes layer and Argo cannot see it: pod stuck `Pending` (unschedulable,
   no nodes match `nodeSelector`/tolerations, insufficient resources), `ImagePullBackOff`,
   `CreateContainerConfigError` (missing secret/configmap), or OOMKilled.

   ```bash
   kubectl -n <namespace> describe pod <pod-name>
   kubectl -n <namespace> get events --sort-by=.lastTimestamp | tail -30
   ```

   The pod name is the node's pod (visible in `argo get -o yaml` under the node's
   `boundaryID`/`displayName`, or via `kubectl get pods -l workflows.argoproj.io/workflow=<wf>`).

This is an escalation, not a substitute. `argo` answers "which step failed and what
did it print"; `kubectl` answers "why did Kubernetes never let the step run." Do not
reach for `kubectl` until the first two steps are exhausted.

## Common failure causes

| Symptom (from `argo get`/`logs`) | Likely cause | Where to confirm |
|---|---|---|
| Node `Failed`, message "exit code 1" | Your command returned non-zero | `argo logs <wf> <node>` |
| Pod stuck `Pending` forever | Unschedulable: nodeSelector/tolerations/resources | `kubectl describe pod` events |
| `ImagePullBackOff` | Bad image ref or missing registry creds | `kubectl describe pod` |
| Empty `main` logs, node failed early | Input artifact/param download failed | `argo logs -c init` |
| Step succeeded but downstream missing outputs | Output artifact upload failed | `argo logs -c wait` |
| Workflow `Error` not `Failed` | Controller-level (RBAC, bad templateRef, quota) | controller logs, `argo get -o yaml` |
| Step killed mid-run | OOMKilled or activeDeadlineSeconds hit | `kubectl describe pod`, check `resources`/timeouts |

`Failed` means a node's pod ran and exited non-zero; `Error` means Argo could not
run the node at all (configuration, RBAC, quota). They point at different layers —
read the phase before deciding where to look.

## `retry` — re-run from the failed node

`argo retry` restarts a *failed* workflow from its failed nodes, **keeping the
successful nodes' results**. Use it when a transient failure (flaky network, a
since-fixed dependency) broke an otherwise-good run and re-doing the completed work
would be wasteful.

```bash
argo retry my-workflow-abcde
argo retry @latest
argo retry my-workflow-abcde --restart-successful --node-field-selector templateName=build
```

`--restart-successful` with a node selector forces specific succeeded nodes to
re-run too — use it when a "successful" step actually produced bad output.

## `resubmit` — re-run from scratch

`argo resubmit` creates a **brand-new** workflow from the same spec. Nothing is
reused. Use it when the input spec or the world changed and you want a clean run,
not a continuation.

```bash
argo resubmit my-workflow-abcde
argo resubmit @latest
argo resubmit my-workflow-abcde --memoized   # reuse memoized step outputs where configured
```

Rule of thumb: **`retry`** to resume a broken run in place; **`resubmit`** to start
over fresh. Retry preserves history and node results; resubmit does not.

## `stop` vs `terminate`

Both halt a running workflow, but they differ in whether cleanup runs — this matters
when your workflow has `onExit` handlers that release locks, post status, or delete
temp resources.

- **`argo stop`** — graceful: shut down running nodes, then **run the `onExit`
  handler and any exit hooks** so cleanup happens. Prefer this.

  ```bash
  argo stop my-workflow-abcde
  ```

- **`argo terminate`** — forceful: kill everything immediately, **skip `onExit`**.
  Use only when a workflow is wedged and you accept that cleanup will not run.

  ```bash
  argo terminate my-workflow-abcde
  ```

Default to `stop`. Reach for `terminate` only when `stop` itself hangs or there is
no safe cleanup to preserve.

## `suspend` and `resume`

`argo suspend` pauses a workflow: running pods finish but no new nodes start.
`argo resume` lets it continue. Use this to hold a pipeline at a gate (manual
approval, an external dependency) without losing progress.

```bash
argo suspend my-workflow-abcde
argo resume my-workflow-abcde
```

These also drive `suspend` template nodes — a workflow can pause itself at an
approval step and wait for `argo resume` (or a resume via the API/UI). For an
automatic timeout on a suspend node, set `spec.templates[].suspend.duration`.

## `delete` — clean up

```bash
argo delete my-workflow-abcde
argo delete @latest
argo delete --completed              # all finished workflows in the namespace
argo delete --older 7d               # anything older than 7 days
argo delete --status Failed          # by phase
```

Deleting removes the Workflow object and its pods. Prefer configuring a workflow
or namespace TTL/GC so cleanup is automatic; use manual `delete --older`/`--completed`
to reclaim a namespace that has accumulated finished runs. Deletion is irreversible
— it discards the node history and any non-archived logs.
