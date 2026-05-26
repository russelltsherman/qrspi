---
name: using-argo-workflows-cli
description: Guide agents managing Argo Workflows via the argo CLI. Use whenever the user asks to submit, list, get, watch, delete, retry, stop, terminate, suspend, or resume workflows; debug failed workflows or pods; manage CronWorkflows (create, suspend, resume, lint); configure retry strategies, resource limits, artifacts, DAG/Steps templates, WorkflowTemplates, or synchronization. Also use for argo lint, kubectl pod diagnostics, debugging OOMKilled/ImagePullBackOff/volume errors, and any Argo CLI or Kubernetes workflow operation.
command: /using-argo-workflows-cli
argument-hint: <argo subcommand or workflow task description>
allowed-tools: Read, Bash(argo:*), Bash(kubectl:*), Bash(which:*)
---

# Using Argo Workflows CLI

Manage Argo Workflows in Kubernetes clusters using the `argo` CLI.

## Prerequisite Check

Before running any Argo commands, verify the tools are available:

```bash
which argo     # Must exist
which kubectl  # Must exist
```

If either is missing, report the error and stop.

## Command Groups

### Submit workflows
```bash
argo submit <file.yaml> -n argo-workflows
argo submit <file.yaml> -n argo-workflows -p key=value   # Pass parameters
argo submit <file.yaml> -n argo-workflows --watch          # Submit and watch
```

### List workflows
```bash
argo list -n argo-workflows
argo list -n argo-workflows --status Running               # Filter by status
```

### Get workflow details
```bash
argo get <workflow-name> -n argo-workflows
argo get <workflow-name> -n argo-workflows -o yaml         # Full spec output
```

### View logs
```bash
argo logs <workflow-name> -n argo-workflows
argo logs <workflow-name> -n argo-workflows -i main        # Single container
argo logs <workflow-name> -n argo-workflows --task-name X   # Specific task
```

### Watch workflow execution
```bash
argo watch <workflow-name> -n argo-workflows
```

### Delete workflows
```bash
argo delete <workflow-name> -n argo-workflows
```

### CronWorkflow management
```bash
argo cron create <file.yaml> -n argo-workflows
argo cron list -n argo-workflows
argo cron get <name> -n argo-workflows
argo cron suspend <name> -n argo-workflows
argo cron resume <name> -n argo-workflows
argo cron delete <name> -n argo-workflows
argo cron lint <file.yaml> -n argo-workflows
```

See `Read .claude/skills/using-argo-workflows-cli/references/cron-and-resources.md` for full CronWorkflow lifecycle, concurrency policy, timezone, history limits, and resource management details.

### Lint workflow YAML
```bash
argo lint <file.yaml>
```

### Retry a failed task
```bash
argo retry <workflow-name> -n argo-workflows --task-name X
```

### Resubmit with cached results
```bash
argo resubmit <workflow-name> -n argo-workflows --mode Cache   # Use cached
argo resubmit <workflow-name> -n argo-workflows --mode Reexecute  # Re-execute all
```

### Stop a running workflow (graceful)
```bash
argo stop <workflow-name> -n argo-workflows
```

### Terminate a running workflow (immediate)
```bash
argo terminate <workflow-name> -n argo-workflows
```

### Suspend a running workflow (pause)
```bash
argo suspend <workflow-name> -n argo-workflows
```

### Resume a suspended workflow
```bash
argo resume <workflow-name> -n argo-workflows
```

## DAG vs Steps Rule

Default to DAG (`dag` template type). Use Steps only when you need explicit ordered sequences with branching logic defined by entry points.

For detailed guidance: `Read .claude/skills/using-argo-workflows-cli/references/template-authoring.md`

## Retry and Error Handling

- Always set `retryStrategy` on templates interacting with external services.
- Use `retryPolicy: "Always"`, `"OnError"`, `"OnFailure"`, or `"Default"`.
- Add `backoff.duration`, `backoff.factor`, and `backoff.maxDuration` for exponential backoff.
- Set `activeDeadlineSeconds` on templates as a safety ceiling.
- Retries require idempotent template logic — add explicit idempotency checks in the task code.

For detailed escalation ladder and common failure modes: `Read .claude/skills/using-argo-workflows-cli/references/debugging-and-errors.md`

## Debugging Escalation Ladder

When a workflow fails, follow this ladder in order:

1. `argo get <name>` — check workflow and task phases.
2. `argo logs <name>` — review task output for exceptions and tracebacks.
3. `kubectl describe pod <pod-name>` — inspect container state, exit codes, restart history.
4. `kubectl get events -n argo-workflows` — check scheduling and cluster-level issues.

For full details on common failures (OOMKilled, ImagePullBackOff, volume errors, pending pods): `Read .claude/skills/using-argo-workflows-cli/references/debugging-and-errors.md`

## Resource Management Rules

- Always set both `resources.requests` and `resources.limits` (cpu and memory) on containers.
- Set `spec.parallelism` on workflows to cap concurrent template execution.
- Use synchronization mutexes when multiple workflows share resources.

For concurrency policy, parallelism, synchronization, and artifact configuration details: `Read .claude/skills/using-argo-workflows-cli/references/cron-and-resources.md`

## Artifact Rules

- Artifacts pass data between templates via `inputs.artifacts` and `outputs.artifacts`.
- Use `from: "{{tasks.X.outputs.artifacts.name}}"` to reference upstream artifacts.
- Set `artifactGC.strategy` — prefer `OnWorkflowCompletion` for production.
- Use S3 or GCS for persistent cross-node artifacts; emptyDir is same-node only.

For full artifact configuration and storage options: `Read .claude/skills/using-argo-workflows-cli/references/cron-and-resources.md`

## When to Read Reference Files

- **Template authoring** (DAG vs Steps, WorkflowTemplate, design patterns): `Read .claude/skills/using-argo-workflows-cli/references/template-authoring.md`
- **Debugging / errors** (escalation ladder, OOMKilled, retry config): `Read .claude/skills/using-argo-workflows-cli/references/debugging-and-errors.md`
- **CronWorkflows / resources** (lifecycle, concurrency, parallelism, artifacts): `Read .claude/skills/using-argo-workflows-cli/references/cron-and-resources.md`
