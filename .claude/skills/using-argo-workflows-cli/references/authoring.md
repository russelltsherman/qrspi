# Authoring workflows and templates

Writing or reviewing a workflow spec. Read this when choosing DAG vs Steps,
composing reusable templates, wiring parameters and artifacts, setting retry and
error handling, or tuning resources and concurrency.

## Contents

- [DAG vs Steps](#dag-vs-steps)
- [Templates: WorkflowTemplate, ClusterWorkflowTemplate, templateRef](#templates-workflowtemplate-clusterworkflowtemplate-templateref)
- [Parameters and variables](#parameters-and-variables)
- [Artifacts](#artifacts)
- [Retry strategy and error handling](#retry-strategy-and-error-handling)
- [Resource management](#resource-management)
- [Linting templates](#linting-templates)

## DAG vs Steps

A workflow's control flow is either a `dag` (nodes with `dependencies`) or `steps`
(an ordered list of stages).

**Default to DAG.** A DAG expresses dependencies explicitly, so independent work
runs in parallel automatically and adding a step means declaring what it depends
on — not re-threading a sequence. Use **Steps only for purely sequential work with
no branching**, where the linear list is genuinely easier to read than a dependency
graph.

```yaml
# DAG — B and C run in parallel after A; D waits for both
dag:
  tasks:
    - name: A
      template: prep
    - name: B
      template: work
      dependencies: [A]
    - name: C
      template: work
      dependencies: [A]
    - name: D
      template: merge
      dependencies: [B, C]
```

In a DAG, gate a task on an upstream result with `depends` (boolean expressions
over node phases), e.g. `depends: "A.Succeeded && (B.Succeeded || B.Skipped)"`.
Prefer `depends` over the older `dependencies` list when you need conditional
joins; use plain `dependencies` for simple "after all of these" edges.

## Templates: WorkflowTemplate, ClusterWorkflowTemplate, templateRef

Factor reusable logic into installed templates instead of copy-pasting spec across
workflows. A reviewed template is the single source of truth; runs reference it.

- **`WorkflowTemplate`** — namespaced reusable template. Install once, reference by
  name from many workflows.
- **`ClusterWorkflowTemplate`** — same, but cluster-scoped: shared across all
  namespaces. Use for org-wide building blocks (a standard build, a notifier).
- **`templateRef`** — how a workflow node calls into an installed template:

  ```yaml
  - name: build
    templateRef:
      name: shared-build           # the (Cluster)WorkflowTemplate name
      template: compile            # the template entry inside it
      clusterScope: true           # set when referencing a ClusterWorkflowTemplate
  ```

Submit a one-off run of an installed template directly with
`argo submit --from workflowtemplate/<name>` (see submission-and-monitoring.md).
Prefer `--from` + `templateRef` over inlining spec so every run shares one
reviewed definition.

## Parameters and variables

Declare inputs under `arguments.parameters` (workflow level) or
`inputs.parameters` (template level); reference them with `{{...}}`:

```yaml
arguments:
  parameters:
    - name: environment
      value: staging          # default; override at submit with -p environment=prod
```

Common variable namespaces:

- `{{inputs.parameters.<name>}}` — a template's declared input.
- `{{workflow.parameters.<name>}}` — a workflow-level argument.
- `{{tasks.<name>.outputs.parameters.<p>}}` (DAG) /
  `{{steps.<name>.outputs.parameters.<p>}}` (Steps) — pass a value from one node
  to the next.
- `{{workflow.name}}`, `{{workflow.uid}}`, `{{workflow.namespace}}` — run identity;
  `{{workflow.uid}}` is the unique, collision-free key for naming outputs.

Keep parameters typed by convention (a value is always a string at the wire level)
and give every input a sensible default so the spec lints and dry-runs without
requiring every `-p`.

## Artifacts

Artifacts move files between steps and to/from external storage (S3, GCS, etc.).
Two conventions prevent the usual failure modes:

**Parameterize the storage key with `{{workflow.uid}}`** so concurrent or repeated
runs never overwrite each other's outputs:

```yaml
outputs:
  artifacts:
    - name: report
      path: /tmp/report.tar.gz
      s3:
        key: "reports/{{workflow.uid}}/report.tar.gz"   # unique per run
```

Argo packages directory artifacts as tarballs; **suffix such keys with `.tgz`** so
the stored object's name reflects its real format and downstream consumers (and
humans) are not surprised by content type.

**Garbage-collect artifacts** so storage does not grow without bound. Set
`spec.artifactGC` to reclaim artifacts when the workflow is deleted or completes:

```yaml
spec:
  artifactGC:
    strategy: OnWorkflowDeletion    # or OnWorkflowCompletion
```

Define the storage backend once in an `artifactRepositoryRef` / the controller's
artifact-repository configmap rather than repeating credentials and bucket config
in every spec.

## Retry strategy and error handling

Make transient failures self-healing with `retryStrategy`. Use **exponential
backoff** so retries do not hammer a struggling dependency:

```yaml
retryStrategy:
  limit: 3
  retryPolicy: OnError          # OnFailure | OnError | OnTransientError | Always
  backoff:
    duration: "30s"             # initial wait
    factor: 2                   # 30s → 60s → 120s
    maxDuration: "10m"          # cap total backoff
```

- **`retryPolicy`** — `OnFailure` retries non-zero exits; `OnError` retries Argo/host
  errors; `OnTransientError` retries only errors marked transient; `Always` retries
  both. Pick the narrowest policy that covers the failure you actually expect —
  retrying a deterministic bug just wastes runs.
- **Idempotency is a precondition for retry.** Only retry steps that are safe to run
  twice. A step that appends to a ledger or sends an email must be made idempotent
  (dedup key, conditional write) before you give it a `retryStrategy`, or retries
  cause duplicates.
- **Timeouts** bound a stuck step independently of retries: set
  `activeDeadlineSeconds` on a template (per-attempt limit) and on the workflow
  `spec` (whole-run limit) so a hung pod fails and frees resources instead of
  blocking forever.
- **`onExit` handlers** run cleanup/notification whether the workflow succeeded or
  failed — release locks, post status, delete temp resources here. `argo stop`
  runs them; `argo terminate` skips them (see debugging-and-lifecycle.md).

## Resource management

Bound what each step consumes and where it runs so one workflow cannot starve the
cluster:

```yaml
container:
  image: my/tool:1.2
  resources:
    requests: { cpu: "500m", memory: "512Mi" }
    limits:   { cpu: "1",    memory: "1Gi" }
nodeSelector:
  workload: batch
tolerations:
  - key: dedicated
    operator: Equal
    value: batch
    effect: NoSchedule
```

- **`requests`/`limits`** — always set both. Requests let the scheduler place the
  pod; limits cap it (memory limit prevents a leak from taking down a node; an OOM
  shows up as a killed step — see common failure causes).
- **`nodeSelector` / `tolerations`** — pin batch workloads to dedicated/tainted
  nodes so they do not compete with services.
- **`parallelism`** — cap concurrent pods at the workflow (`spec.parallelism`) or
  controller level to avoid a wide DAG saturating quota.
- **`synchronization`** — use a `mutex` or `semaphore` (backed by a configmap) to
  serialize access to a shared resource across workflows, e.g. a single-writer
  deploy or a rate-limited external API:

  ```yaml
  synchronization:
    mutex:
      name: production-deploy
  ```

## Linting templates

Lint authored specs and templates before installing or submitting — it catches
schema and reference errors client-side in a fraction of a second:

```bash
argo lint workflow.yaml
argo lint workflowtemplate.yaml
argo template lint workflowtemplate.yaml     # validate a WorkflowTemplate specifically
```

Lint validates structure and references, not runtime behavior. Pair it with a
`--dry-run -o yaml` submit to confirm parameter substitution before a real run.
