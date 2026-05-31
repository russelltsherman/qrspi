# CronWorkflows and debugging

**Targeted version:** Argo Workflows **v3.5.x** (principle-based — the lifecycle and escalation steps
below are stable across the 3.x line; confirm flags with `argo cron --help` / `argo --help`).

## CronWorkflow lifecycle

A `CronWorkflow` wraps a `workflowSpec` with a schedule and spawns `Workflow` objects on a cron
timer. Manage the full lifecycle non-interactively with explicit `--namespace`.

```bash
argo cron lint   -n ci cron.yaml                 # validate before creating
argo cron create -n ci cron.yaml
argo cron list   -n ci -o wide                    # see schedule, last-run, next-run
argo cron get    -n ci nightly-build -o yaml      # full status incl. activeWorkflows
argo cron suspend -n ci nightly-build             # pause scheduling (does not delete)
argo cron resume  -n ci nightly-build             # re-enable scheduling
argo cron delete  -n ci nightly-build
```

Lifecycle commands: **create, list, get, suspend, resume, delete, lint.**

### Key spec fields

```yaml
spec:
  schedules:                       # list of cron expressions (3.5+; older: `schedule:`)
    - "0 2 * * *"
  timezone: "America/New_York"
  concurrencyPolicy: "Forbid"      # Allow | Forbid | Replace
  startingDeadlineSeconds: 120     # skip a run missed by more than this
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  suspend: false
  workflowSpec: { ... }            # the Workflow spec to run each tick
```

- **`concurrencyPolicy`:** `Forbid` (skip if previous still running — the safe default for
  non-overlapping jobs), `Replace` (cancel the old, start new), `Allow` (overlap permitted).
- **History limits** bound how many finished child workflows are retained (etcd hygiene).
- **`startingDeadlineSeconds`** prevents a flood of catch-up runs after controller downtime.
- Validate the schedule and spec with `argo cron lint` before `create`.

## Debugging escalation path

Work outside-in: workflow status → step logs → Kubernetes pod/scheduling events. Stop as soon as the
failure is explained.

### Step 1 — `argo get` (workflow status)

```bash
argo get -n ci @latest                              # which node failed, and the message
argo get -n ci my-wf-abcde --node-field-selector phase=Failed -o yaml
```

Read the failed node's `message`, `phase`, and `exitCode`. This usually localizes the problem to a
single template/task. If a node is `Pending` for a long time, it's a scheduling/resource issue → skip
to Step 3.

### Step 2 — `argo logs` (step/container logs)

```bash
argo logs -n ci my-wf-abcde --container main          # application-level failure
argo logs -n ci my-wf-abcde --previous                # logs from a crashed/restarted container
argo logs -n ci my-wf-abcde --grep ERROR --timestamps
```

Use this when `argo get` shows the node *ran* but failed (non-zero exit, app error). The logs carry
the actual stderr/stdout of the workload.

### Step 3 — `kubectl describe` (pod / scheduling events)

```bash
kubectl describe pod -n ci -l workflows.argoproj.io/workflow=my-wf-abcde
kubectl describe workflow -n ci my-wf-abcde
kubectl get events -n ci --sort-by=.lastTimestamp | tail -n 30
```

Use this when the pod never produced useful logs: `Pending`/`Unschedulable` (insufficient
cpu/memory, no matching `nodeSelector`/taint), `ImagePullBackOff`, `CreateContainerConfigError`
(missing secret/configmap), or OOMKill. The Events section names the exact reason.

**Summary of the escalation:** `argo get` (what failed) → `argo logs` (why the workload failed) →
`kubectl describe` (why the pod couldn't run). Always start at the top and only descend when the
current layer doesn't explain the failure.
