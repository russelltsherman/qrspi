# Debugging and Error Handling

## Escalation Ladder

### 1. `argo get <name>` — workflow state
Shows phase (Pending/Running/Succeeded/Failed/Error), task phases, start/finish times, failure mechanism.

### 2. `argo logs <name>` — task output
All logs: `argo logs <name> -n ns`. Single container: `-i main`. Specific task: `--task-name X`. Use `--follow` for live streaming.

### 3. `kubectl describe pod <pod>` — pod diagnostics
Container state, restart count, exit code, events. Check `Last State` for restart history and OOMKilled.

### 4. `kubectl get events -n argo-workflows` — cluster diagnostics
Scheduling failures, node issues, resource quota violations for Pending or FailCreate pods.

## Common Failure Modes

- **OOMKilled (exit 137)**: increase `resources.limits.memory`. Check `kubectl describe pod` Last State.
- **ImagePullBackOff**: wrong image name/tag, missing registry credentials. Check pod events for `Failed to pull image`.
- **Volume mount errors**: PVC missing, wrong access mode, node can't mount. Check for `MountVolume.SetUp failed`.
- **Pending pods**: insufficient node resources, PVC Pending, node selectors/taints mismatch. Check `kubectl get events`.

## Retry Configuration

### Template-level (preferred)
```yaml
retryStrategy:
  limit: 3
  retryPolicy: "Always"
  backoff:
    duration: "5s"
    factor: 2
    maxDuration: "1m"
```

### retryPolicy options
- `Always` — retry every failure.
- `OnError` — transient errors (connection refused, 5xx).
- `OnFailure` — exit code > 0 or phase = Failed.
- `Default` — same as OnError unless OOMKilled.

### Key rules
- Retries require idempotent logic — add explicit idempotency checks in the task.
- Set `activeDeadlineSeconds` on templates as a safety ceiling.
- Workflow-level retry in `spec.retryStrategy` applies to the entire workflow, not individual tasks.
