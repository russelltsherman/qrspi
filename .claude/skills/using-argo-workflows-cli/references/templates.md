# Authoring workflow templates: DAG vs Steps, parameters, scope

**Targeted version:** Argo Workflows **v3.5.x** (principle-based — the structural concepts below are
stable across the 3.x line; verify field names against the cluster CRD when in doubt).

## DAG vs Steps — decision criteria

Both express multi-task workflows; choose by the shape of your dependencies.

**Use `dag` when:**

- Tasks form a dependency graph (fan-out / fan-in), not a strict line.
- You want maximum parallelism — independent tasks run concurrently automatically.
- A task should start as soon as *its* dependencies finish, not when a whole prior group finishes.
- You need conditional edges (`depends: "a.Succeeded && b.Failed"`).

```yaml
templates:
  - name: pipeline
    dag:
      tasks:
        - name: build
          template: build-tmpl
        - name: test-unit
          template: test-tmpl
          depends: build
        - name: test-int
          template: test-tmpl
          depends: build
        - name: deploy
          template: deploy-tmpl
          depends: "test-unit && test-int"
```

**Use `steps` when:**

- The flow is essentially linear or a few sequential groups.
- You want explicit ordered phases; parallel tasks within a phase share a list entry.
- Readability of a simple sequence matters more than graph expressiveness.

```yaml
templates:
  - name: pipeline
    steps:
      - - name: build            # sequential phase
          template: build-tmpl
      - - name: test-unit        # this inner list runs in parallel
          template: test-tmpl
        - name: test-int
          template: test-tmpl
      - - name: deploy
          template: deploy-tmpl
```

Steps semantics: outer list = sequential; inner list (double `- -`) = parallel within the step.

**Rule of thumb:** reach for `steps` first for simple sequences; switch to `dag` the moment you have
real fan-out/fan-in or conditional dependencies.

## Template authoring

A `Workflow`/`WorkflowTemplate` `spec` has an `entrypoint` plus a list of `templates`. Template kinds:

- **container** — runs a single container (the workhorse).
- **script** — inline script body, exposes its stdout as `outputs.result`.
- **resource** — creates/patches a Kubernetes resource and optionally waits on a success condition.
- **suspend** — pauses for manual or timed approval.
- **dag** / **steps** — orchestrate other templates (above).

Keep leaf templates small and single-purpose; compose them with `dag`/`steps` orchestrators.

## Parameters, inputs/outputs, and variable substitution

- **Workflow-level inputs:** `spec.arguments.parameters` (override at submit with `-p k=v` /
  `--parameter-file`). Provide defaults so the workflow is runnable without every flag.
- **Template inputs/outputs:** `inputs.parameters`, `inputs.artifacts`; `outputs.parameters`
  (from a file path or `result`), `outputs.artifacts`.
- **Variable substitution** uses `{{...}}`:
  - `{{workflow.parameters.x}}`, `{{inputs.parameters.x}}`
  - `{{tasks.<name>.outputs.parameters.y}}` (DAG) / `{{steps.<name>.outputs.parameters.y}}` (Steps)
  - `{{workflow.name}}`, `{{workflow.namespace}}`, `{{pod.name}}`, `{{retries}}`
- Pass outputs between tasks by wiring one task's `outputs` into another's `arguments`.

## WorkflowTemplate vs ClusterWorkflowTemplate (scope)

- **`WorkflowTemplate`** — **namespaced**. Reusable spec referenced via
  `--from workflowtemplate/<name>` or `workflowTemplateRef` within a namespace. Use for team- or
  app-scoped reusable pipelines.
- **`ClusterWorkflowTemplate`** — **cluster-scoped**. Referenced from any namespace via
  `--from clusterworkflowtemplate/<name>` or `workflowTemplateRef: { clusterScope: true }`. Use for
  shared, org-wide building blocks (common lint, notify, cleanup steps).

Decision: start namespaced (`WorkflowTemplate`); promote to `ClusterWorkflowTemplate` only when the
template is genuinely shared across namespaces and you accept cluster-wide governance of it.
Reference templates rather than inlining specs so logic stays versioned and DRY.
