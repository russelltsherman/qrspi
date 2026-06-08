---
name: using-argo-workflows-cli
description: "Submit, monitor, debug, and manage Argo Workflows from the CLI. Use when the user is submitting a workflow, reading workflow logs, debugging a failed step, retrying or resubmitting a run, managing cron schedules, authoring WorkflowTemplates or DAGs, or operating the argo CLI in any way. Trigger on any of: argo submit, argo get, argo logs, argo retry, argo resubmit, argo stop, argo terminate, argo suspend, argo resume, argo delete, argo watch, argo lint, argo cron, argo template, WorkflowTemplate, CronWorkflow, DAG template, steps template, Argo Workflows, 'my workflow failed', 'check argo logs', 'argo parallelism', artifact configuration, retry strategy, or backoff. Also trigger on: 'how do I submit a workflow', 'watch argo workflow', 'argo dry run', 'workflow is stuck', or any question about Argo Workflows concepts."
command: /using-argo-workflows-cli
argument-hint: <what you want to do with Argo Workflows>
allowed-tools: Bash, Read
---

# Using the Argo Workflows CLI

This skill covers operating Argo Workflows from the `argo` CLI — submitting runs,
reading output, debugging failures, managing the workflow lifecycle, authoring
templates, and scheduling cron jobs. The goal is safe, observable workflow
operations: you know what ran, why it failed, and how to recover. Command-group
detail lives in the `references/` files below; this body routes you to the right
one and captures conventions that apply everywhere.

## Prerequisite check — confirm `argo` is available

Before any `argo` command, verify the binary is reachable:

```bash
argo version
```

If this fails (command not found, connection refused, permission denied, or any
other error): **STOP. Surface the exact command and the exact error output.
Do not attempt workarounds, alternate tools, or kubectl substitutes.** The
binary must be installed and the Kubernetes context must be reachable before
proceeding. Common reasons this fails:

- `argo` is not installed or not on `$PATH` — install the CLI matching your
  server version from the Argo Workflows GitHub releases page.
- No valid kubeconfig / wrong context — run `kubectl cluster-info` to confirm
  the cluster is reachable.
- Argo server not deployed in the target namespace — confirm with
  `kubectl -n argo get deploy workflow-controller`.

Only continue once `argo version` exits cleanly.

## Decision routing

Use the section that matches your task, then read the linked reference file for
detailed command syntax, flags, and examples.

### Submitting, linting, and monitoring workflows

You want to submit a workflow spec, dry-run it, pass parameters, or observe a
running workflow (list, get status, stream logs, watch live).

→ Read [`references/submission-and-monitoring.md`](references/submission-and-monitoring.md)

Covers: `submit`, `lint`, `list`, `get`, `logs`, `watch`, `@latest` shorthand,
parameter overrides, `--from` (reuse a template), container selection.

### Debugging failures and lifecycle operations

A workflow step has failed, is stuck, or you need to act on a running/completed
workflow (stop it, retry from a failed node, resubmit from scratch, suspend,
resume, or clean it up).

→ Read [`references/debugging-and-lifecycle.md`](references/debugging-and-lifecycle.md)

Covers: debugging escalation path (`argo get` → `argo logs` → `kubectl describe`
pod), common failure causes, `retry`, `resubmit`, `stop`, `terminate`, `suspend`,
`resume`, `delete`.

### Authoring workflow specs and templates

You are writing or reviewing a workflow spec: choosing DAG vs Steps, composing
WorkflowTemplates, wiring parameters and artifacts, setting retry strategy /
backoff, or tuning resource requests and parallelism.

→ Read [`references/authoring.md`](references/authoring.md)

Covers: DAG vs Steps decision criteria, WorkflowTemplate / ClusterWorkflowTemplate
/ `templateRef`, parameter and variable patterns, artifact configuration (key
parameterization, `.tgz` suffix, GC), retry strategy with exponential backoff,
resource management (requests/limits, nodeSelector, tolerations, parallelism,
synchronization).

### Cron workflows

You are creating, listing, suspending, resuming, or deleting a CronWorkflow, or
you need to understand concurrency policy and timezone handling.

→ Read [`references/cron-workflows.md`](references/cron-workflows.md)

Covers: `cron create`, `cron list`, `cron suspend`, `cron resume`, `cron delete`,
`cron lint`, concurrency policy (`Allow` / `Forbid` / `Replace`), timezone.

## Cross-cutting conventions

- **Namespace flag.** Most `argo` commands default to the `argo` namespace; pass
  `-n <namespace>` when workflows live elsewhere. Set `ARGO_NAMESPACE` in your
  environment to avoid repeating it.
- **`@latest` shorthand.** In `get`, `logs`, `watch`, `retry`, and `resubmit`,
  `@latest` refers to the most-recently submitted workflow in the namespace — saves
  copying the generated name during development.
- **Dry-run before submit.** `argo lint <file>` validates the spec client-side
  without touching the cluster. Use it in CI and before every first submit of a
  new template.
- **Output formats.** Add `-o json` or `-o yaml` to `argo get` and `argo list` for
  machine-readable output (useful for scripting and debugging).
