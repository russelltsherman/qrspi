# Submission and monitoring

Submitting workflows and observing what they do. Read this when you want to run a
spec, validate it before running, pass parameters, reuse a template, or watch a
running workflow.

## Contents

- [Linting before submit](#linting-before-submit)
- [Submitting a workflow](#submitting-a-workflow)
- [Passing parameters](#passing-parameters)
- [Submitting from a template (`--from`)](#submitting-from-a-template---from)
- [Listing workflows](#listing-workflows)
- [Getting workflow status (`get`)](#getting-workflow-status-get)
- [Reading logs (`logs`)](#reading-logs-logs)
- [Watching live (`watch`)](#watching-live-watch)
- [`@latest` shorthand](#latest-shorthand)
- [Container selection](#container-selection)

## Linting before submit

`argo lint` validates a spec client-side against the installed CRDs without
creating anything on the cluster. Lint first so a typo fails in a quarter second
instead of after a pod schedules and crashes.

```bash
argo lint workflow.yaml
argo lint ./manifests/            # lint every spec in a directory
```

Use lint in CI and before the first submit of any new template. It catches schema
errors, unknown fields, and bad template references — not runtime failures.

## Submitting a workflow

`argo submit` creates a Workflow from a spec and returns its generated name.

```bash
argo submit workflow.yaml                 # fire and forget, returns the name
argo submit --watch workflow.yaml         # submit then stream status until done
argo submit --wait workflow.yaml          # submit, block until done, no live UI
argo submit --log workflow.yaml           # submit and stream logs
```

`--watch` is the most useful default during development: you see each node move
through Pending → Running → Succeeded/Failed without copying the name into a
separate `get`.

Add `--dry-run -o yaml` to render the fully-resolved manifest (parameters
substituted, defaults applied) without submitting — useful for confirming what
the cluster would actually receive:

```bash
argo submit --dry-run -o yaml workflow.yaml
```

## Passing parameters

Override `spec.arguments.parameters` at submit time with `-p`:

```bash
argo submit workflow.yaml -p message=hello -p replicas=3
argo submit workflow.yaml --parameter-file params.yaml
```

`-p` values are strings; the workflow's parameter defaults define the contract.
For anything beyond a few values, a `--parameter-file` (YAML map of name→value)
keeps the invocation readable and reviewable.

## Submitting from a template (`--from`)

`--from` creates a Workflow from an already-installed `WorkflowTemplate`,
`ClusterWorkflowTemplate`, or `CronWorkflow` instead of from a local file. This is
the production pattern: templates are installed once and reviewed, runs reference
them by name.

```bash
argo submit --from workflowtemplate/my-template -p env=staging
argo submit --from clusterworkflowtemplate/shared-build
argo submit --from cronworkflow/nightly-report      # trigger a cron run on demand
```

Prefer `--from` over re-submitting a raw file when a template exists — it keeps a
single reviewed source of truth and avoids spec drift between runs.

## Listing workflows

```bash
argo list                      # workflows in the current namespace
argo list -A                   # across all namespaces
argo list --status Running     # filter by phase (Running/Failed/Succeeded/...)
argo list --running            # shorthand for active workflows
argo list -o name              # just the names, scriptable
argo list --older 7d           # candidates for cleanup
```

`argo list` is the entry point when you do not yet know a workflow's generated
name. Combine with `-o name` to feed names into `get`, `logs`, or `delete`.

## Getting workflow status (`get`)

`argo get` shows the node tree, each node's phase, durations, and the message on
any failed node — your first stop when something looks wrong.

```bash
argo get my-workflow-abcde
argo get @latest
argo get my-workflow-abcde -o json     # machine-readable, for scripting/jq
argo get my-workflow-abcde --node-field-selector phase=Failed
```

Read the node tree top-down: the first node with a non-Succeeded phase is where
the failure originates. Note its name — you pass it to `argo logs` next.

## Reading logs (`logs`)

```bash
argo logs my-workflow-abcde                       # all pods in the workflow
argo logs my-workflow-abcde my-step-node          # one node's logs
argo logs my-workflow-abcde -f                     # follow live
argo logs my-workflow-abcde --previous            # logs of a crashed/restarted container
argo logs @latest -f
```

When a node failed, scope logs to that node name (from `argo get`) rather than
dumping every pod — the relevant error is almost always in the failing node.

## Watching live (`watch`)

`argo watch` opens a live, auto-refreshing view of one workflow's node tree.

```bash
argo watch my-workflow-abcde
argo watch @latest
```

Use `watch` for an interactive look at a long-running DAG; use `argo logs -f` when
you care about a specific container's output rather than the topology.

## `@latest` shorthand

`@latest` resolves to the most recently created workflow in the namespace. It
works in `get`, `logs`, `watch`, `retry`, and `resubmit`, so during iterative
development you can skip copying the generated name:

```bash
argo submit --watch workflow.yaml
argo logs @latest -f
argo retry @latest
```

`@latest` is per-namespace and time-based — in a shared namespace with concurrent
submissions it may not be *your* workflow. Use the explicit name in CI or shared
environments.

## Container selection

A workflow pod runs the user `main` container alongside Argo's `wait` and `init`
containers. By default `argo logs` shows `main`; target another with `-c`:

```bash
argo logs my-workflow-abcde -c init      # debug artifact/input download failures
argo logs my-workflow-abcde -c wait      # debug artifact upload / output capture
```

If a step fails before your code runs (inputs never arrive) or its outputs never
appear, the cause is usually in `init` or `wait`, not `main` — check those
containers before assuming your command is broken.
