---
name: using-argo-workflows-cli
description: Author, run, and operate Argo Workflows from the command line. Use when the user works with the `argo` CLI, writes or reviews a Workflow / WorkflowTemplate / CronWorkflow manifest, chooses DAG vs Steps, sets retry/backoff or resource limits, or debugs a failed or stuck workflow run on Kubernetes.
command: /using-argo-workflows-cli
argument-hint: <what you want to do with Argo Workflows>
allowed-tools: Read, Bash(argo:*), Bash(kubectl:*)
---

# Using the Argo Workflows CLI

General-purpose guidance for working with [Argo Workflows](https://argoproj.github.io/argo-workflows/)
from the command line. This is a capability skill (reusable reference), not a QRSPI phase. Invoke it
whenever you submit, inspect, template, schedule, or debug Argo Workflows.

**Targeted version:** Argo Workflows / `argo` CLI **v3.5.x** (principle-based; flags below are stable
across the 3.x line — confirm exact flags with `argo <command> --help` against the cluster's version).

## When to use

Use this skill when any of the following is true:

- You are constructing or reviewing an `argo` CLI invocation (submit, get, logs, list, lifecycle).
- You are authoring or editing a `Workflow`, `WorkflowTemplate`, `ClusterWorkflowTemplate`, or
  `CronWorkflow` manifest and need to choose between DAG and Steps, parameterize it, or set
  retry/backoff, timeouts, parallelism, or resource limits.
- A workflow has failed, is stuck/pending, or is producing unexpected output and you need a
  systematic debugging path.

Do **not** use it for cluster install/upgrade of the Argo controller itself, or for Argo CD
(a different project).

## Operating conventions (always apply)

- **Non-interactive by default.** Every invocation is scriptable: pass an explicit `--namespace`
  (never rely on the current kube-context default), avoid prompts, and prefer flags over interactive
  selection. Use `-o json`/`-o yaml`/`-o name` when output is consumed by a script.
- **Validate before you submit.** Run `argo lint <file>` and/or `argo submit --dry-run -o yaml`
  before a real `argo submit`. Never submit an unvalidated manifest to a live namespace.
- **Templates over inline.** Prefer `WorkflowTemplate` / `ClusterWorkflowTemplate` references over
  copy-pasted inline specs so logic is reusable and version-controlled.

## Decision-first overview

Each item below is the one-line summary; open the named reference for the full treatment.

- **DAG vs Steps.** Use **DAG** when tasks have a dependency graph with fan-out/fan-in and you want
  maximum parallelism; use **Steps** for simple linear/grouped sequences. (→ `references/templates.md`)
- **Retry & backoff.** Set a `retryStrategy` with `limit` + exponential `backoff`
  (`duration`/`factor`/`maxDuration`) and an explicit `retryPolicy`; default to retrying transient
  errors only. (→ `references/reliability.md`)
- **Resource conventions.** Always set container resource `requests`/`limits`, bound concurrency with
  `parallelism` and `synchronization`, and use `nodeSelector`/`tolerations` for placement.
  (→ `references/reliability.md`)
- **Artifact best practices.** Parameterize artifact keys, scope them per-run, and configure
  artifact GC so storage does not leak. (→ `references/reliability.md`)
- **CronWorkflow lifecycle.** Manage scheduled workflows with the cron sub-commands
  (create/list/get/suspend/resume/delete/lint); set `concurrencyPolicy` and history limits.
  (→ `references/cron-and-debugging.md`)
- **Debugging escalation.** Walk the path `argo get` → `argo logs` → `kubectl describe`
  (workflow status → step logs → pod/scheduling events). (→ `references/cron-and-debugging.md`)

## References

Read these on demand — open the one that matches the task, not all of them.

- **`references/cli-commands.md`** — Open when constructing or reviewing any `argo` command. Full
  catalog of all command groups (submit, get, logs, list, delete, retry, resubmit, stop, terminate,
  suspend, resume, watch, lint, cron, template) with their key flags and the non-interactive /
  scriptable conventions.
- **`references/templates.md`** — Open when authoring or restructuring a workflow spec: DAG vs Steps
  decision criteria, template authoring, parameters/inputs/outputs and variable substitution, and
  `WorkflowTemplate` vs `ClusterWorkflowTemplate` scoping.
- **`references/reliability.md`** — Open when making a workflow robust or production-ready: retry
  strategy and exponential backoff, error handling, timeouts (`activeDeadlineSeconds`), resource
  management (limits, `nodeSelector`, `parallelism`, `synchronization`), and artifact best practices
  (keys, parameterization, GC).
- **`references/cron-and-debugging.md`** — Open when scheduling recurring runs or diagnosing a
  failed/stuck run: full `CronWorkflow` lifecycle and the `argo get` → `argo logs` →
  `kubectl describe` debugging escalation path.
